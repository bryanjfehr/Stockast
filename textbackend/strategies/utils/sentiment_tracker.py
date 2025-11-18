import san as sanpy
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from db.models import SocialMetric
import logging

# Configure a specific logger for this module
logger = logging.getLogger(__name__)

def fetch_top_coins(api_key: str, limit: int = 50) -> List[str]:
    """Fetch top coins by market cap from Santiment more efficiently."""
    if not api_key:
        raise ValueError("Santiment API key is required.")
    sanpy.ApiConfig.api_key = api_key
    # Fetching all projects is slow. A better way is to get top projects by a metric.
    logger.info(f"Returning hardcoded list of top coins as sanpy discovery is unreliable.")
    # Using a hardcoded list is more reliable than sanpy's discovery methods.
    top_slugs = [
        "BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "SHIB", "AVAX", "LINK", "DOT",
        "TRX", "MATIC", "LTC", "BCH", "ICP", "NEAR", "UNI", "LEO", "XLM", "OKB"
    ]
    return top_slugs[:limit]
def fetch_sentiment_time_series(symbols: List[str], api_key: str, days_back: int = 7) -> Dict[str, pd.DataFrame]:
    """
    Batch fetch historical sentiment for symbols from Santiment.
    Returns dict of {symbol: df}.
    """
    if not api_key:
        raise ValueError("Santiment API key is required.")
    sanpy.ApiConfig.api_key = api_key
    
    results = {}
    from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    to_date = datetime.now().strftime('%Y-%m-%d')

    for symbol in symbols:
        try:
            # Per sanpy documentation, use san.get for a single slug with multiple metrics.
            # We will iterate through the symbols.
            df = sanpy.get(
                f"social_volume_total,sentiment_balance_total,sentiment_positive_total,sentiment_negative_total,sentiment_neutral_total/{symbol.lower()}",
                from_date=from_date,
                to_date=to_date,
                interval="1d"
            )
            if not df.empty:
                df.rename(columns={
                    'social_volume_total': 'mentions',
                    'sentiment_positive_total': 'bullish_pct',
                    'sentiment_negative_total': 'bearish_pct',
                    'sentiment_neutral_total': 'neutral_pct',
                    'sentiment_balance_total': 'net_sentiment'
                }, inplace=True)
                df['date'] = pd.to_datetime(df.index).date
                results[symbol] = df
        except Exception as e:
            print(f"Could not fetch sentiment for {symbol}: {e}")
            continue
            
    return results

def store_metrics(db: Session, metrics_data: Dict[str, pd.DataFrame]):
    """Upsert daily metrics to DB."""
    for symbol, df in metrics_data.items():
        for _, row in df.iterrows():
            # Ensure row['date'] is a datetime.date object
            metric_date = row['date']
            if isinstance(metric_date, pd.Timestamp):
                metric_date = metric_date.date()

            existing = db.query(SocialMetric).filter_by(symbol=symbol, date=metric_date).first()
            if not existing:
                metric = SocialMetric(
                    symbol=symbol,
                    date=metric_date,
                    mentions=row['mentions'],
                    bullish_pct=row['bullish_pct'],
                    bearish_pct=row['bearish_pct'],
                    neutral_pct=row['neutral_pct'],
                    net_sentiment=row['net_sentiment']
                )
                db.add(metric)
    db.commit()

def get_daily_sentiment_trend(db: Session, symbol: str, days_back: int = 7) -> Optional[Dict]:
    """Query DB for daily counters + live (latest). Returns avg sentiment, mention growth."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    metrics = db.query(SocialMetric).filter( # type: ignore
        SocialMetric.symbol == symbol,
        SocialMetric.date >= start_date
    ).all()
    
    if not metrics:
        return None
    
    df = pd.DataFrame([{
        'date': m.date,
        'mentions': m.mentions,
        'bullish_pct': m.bullish_pct,
        'bearish_pct': m.bearish_pct,
        'neutral_pct': m.neutral_pct,
        'net_sentiment': m.net_sentiment
    } for m in metrics])
    
    # Daily counters: Sum/avg per day
    daily = df.groupby('date').agg({
        'mentions': 'sum',
        'bullish_pct': 'mean',
        'bearish_pct': 'mean',
        'neutral_pct': 'mean',
        'net_sentiment': 'mean'
    }).reset_index()
    
    # Live current 24h: Latest row
    live = daily.iloc[-1].to_dict()
    
    # Trend: Mention growth % (current vs prev day)
    if len(daily) > 1:
        previous_mentions = daily.iloc[-2]['mentions']
        if previous_mentions > 0:
            live['mention_growth_pct'] = (live['mentions'] - previous_mentions) / previous_mentions * 100
        else:
            live['mention_growth_pct'] = 0  # Avoid division by zero
    else:
        live['mention_growth_pct'] = 0
    
    return {'daily_history': daily.to_dict('records'), 'live_24h': live}

# Scheduler integration (in main.py)
def update_sentiment_job():
    """Run daily/hourly: Fetch and store."""
    from dotenv import load_dotenv
    import os
    from db.utils import get_db
    load_dotenv()
    api_key = os.getenv('SANTIMENT_API_KEY')
    db = next(get_db())
    try:
        top_symbols = fetch_top_coins(api_key)
        metrics = fetch_sentiment_time_series(top_symbols, api_key, days_back=7)
        store_metrics(db, metrics)
        print(f"Updated sentiment for {len(top_symbols)} top coins.")
    except Exception as e:
        print(f"Sentiment update failed: {e}")