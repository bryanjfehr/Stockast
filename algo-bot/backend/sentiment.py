# sentiment.py
import san
import logging
from datetime import datetime, timedelta, timezone
from config import SANTIMENT_API_KEY
from db import save_sentiment_daily_data, get_sentiment_daily_data
import numpy as np # Added for np.tanh

san.ApiConfig.api_key = SANTIMENT_API_KEY  # Set once

logger = logging.getLogger(__name__)


def fetch_and_cache_sentiment(symbol: str, slug: str, days_back: int = 30):
    """Fetch recent daily, cache, return latest dict."""
    # The sentiment_daily table should be created by db.create_tables() on startup.
    
    # 1. Try to get data from cache
    to_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back + 7)).strftime('%Y-%m-%d')  # Extra for avg
    
    cached_df = get_sentiment_daily_data(symbol, days_back + 7) # Fetch a bit more for moving averages
    
    # Check if cached data is sufficient (e.g., covers the requested period)
    if not cached_df.empty and len(cached_df) >= days_back: # At least days_back for computation
        logger.info(f"Using cached sentiment for {symbol}")
        return compute_sentiment_score(cached_df)
    
    # 2. If not sufficient, fetch fresh data from Santiment API
    logger.info(f"Fetching fresh sentiment data for {slug}...")
    try:
        social_df = san.get(
            "social_volume_total",
            slug=slug,
            from_date=from_date,
            to_date=to_date,
            interval="1d"
        )
        sentiment_df = san.get(
            "sentiment_balance_total",
            slug=slug,
            from_date=from_date,
            to_date=to_date,
            interval="1d"
        )
        if social_df.empty or sentiment_df.empty:
            logger.warning(f"No sentiment data for {slug}")
            return {'sentiment_score': 0.0, 'social_volume': 0, 'vol_spike': False}
        
        merged = pd.merge(social_df, sentiment_df, on='datetime')
        merged.rename(columns={'value_x': 'social_volume', 'value_y': 'sentiment_balance'}, inplace=True)
        merged['symbol'] = symbol # Add symbol column for saving
        
        # 3. Save newly fetched data to DB
        save_sentiment_daily_data(symbol, merged)
        
        # Combine cached and new data to ensure we have a full history for computation
        combined_df = pd.concat([cached_df, merged]).drop_duplicates(subset=['datetime']).sort_values('datetime').reset_index(drop=True)
        
        return compute_sentiment_score(combined_df)
    
    except Exception as e:
        logger.error(f"Sentiment fetch error for {slug}: {e}")
        return {'sentiment_score': 0.0, 'social_volume': 0, 'vol_spike': False}

def compute_sentiment_score(df: pd.DataFrame) -> dict:
    """Normalize latest sentiment."""
    if df.empty:
        return {'sentiment_score': 0.0, 'social_volume': 0, 'vol_spike': False}
    
    latest = df.iloc[-1]
    balance = latest['sentiment_balance']
    volume = latest['social_volume']
    
    # Normalize balance
    sentiment_score = np.tanh(balance * 25)  # Amplify: 0.03 -> ~0.64, 0.09 -> ~0.95
    
    # Volume spike
    if len(df) < 7: # Ensure enough data points for tail(7)
        avg_vol = df['social_volume'].mean()
    else:
        avg_vol = df['social_volume'].tail(7).mean()
    vol_spike = volume > avg_vol * 1.5
    
    # Boost if spike + positive
    if vol_spike and sentiment_score > 0:
        sentiment_score = min(sentiment_score * 1.3, 1.0)  # Cap at 1
    
    return {
        'sentiment_score': sentiment_score,
        'social_volume': volume,
        'vol_spike': vol_spike,
        'raw_balance': balance
    }

# Slug map (add more)
SLUG_MAP = {
    'DOGEUSDT': 'dogecoin',
    'BTCUSDT': 'bitcoin',
    'ETHUSDT': 'ethereum',
    # ...
}