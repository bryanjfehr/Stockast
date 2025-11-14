import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv('LUNARCRUSH_API_KEY')
BASE_URL = 'https://api.lunarcrush.com/v4'
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

def fetch_top_50_coins() -> List[str]:
    """Fetch top 50 coins by social mentions (24h). Sort client-side."""
    params = {
        'data': 'assets',  # Or 'coins' for crypto-only
        'key': API_KEY,
        'sort': 'social_volume_24h',  # Proxy for mentions
        'limit': 50,
        'desc': 'true'
    }
    response = requests.get(f'{BASE_URL}/coins', params=params, headers=HEADERS)
    if response.status_code != 200:
        raise ValueError(f"API error: {response.text}")
    
    data = response.json().get('data', [])
    symbols = [coin['symbol'] for coin in data[:50]]  # Top 50
    return symbols

def fetch_sentiment_time_series(symbols: List[str], days_back: int = 7) -> Dict[str, pd.DataFrame]:
    """Batch fetch historical + current 24h sentiment/mentions for symbols (daily interval).
    Returns dict of {symbol: df with cols: date, mentions, bullish_pct, bearish_pct, neutral_pct}.
    """
    # Batch symbols (API supports comma-separated up to ~50)
    symbols_str = ','.join(symbols)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    params = {
        'data': 'timeSeries',
        'symbol': symbols_str,
        'interval': '1d',  # Daily 24h periods
        'timeframe': days_back,
        'key': API_KEY
    }
    response = requests.get(f'{BASE_URL}/timeSeries', params=params, headers=HEADERS)
    if response.status_code != 200:
        raise ValueError(f"Time-series error: {response.text}")
    
    results = {}
    data = response.json().get('data', [])
    for entry in data:
        symbol = entry['symbol']
        df = pd.DataFrame(entry['timeSeries'])  # Assumes array of daily dicts
        df['date'] = pd.to_datetime(df['timeStart']).dt.date  # Parse date
        df = df[['date', 'social_mentions', 'sentiment_bullish', 'sentiment_bearish', 'sentiment_neutral']]  # Key metrics
        df.rename(columns={
            'social_mentions': 'mentions',
            'sentiment_bullish': 'bullish_pct',
            'sentiment_bearish': 'bearish_pct',
            'sentiment_neutral': 'neutral_pct'
        }, inplace=True)
        results[symbol] = df
    
    # For live current 24h: It's the latest row in time-series (API provides real-time-ish)
    return results

def store_metrics(db: Session, metrics_data: Dict[str, pd.DataFrame]):
    """Upsert daily metrics to DB."""
    for symbol, df in metrics_data.items():
        for _, row in df.iterrows():
            existing = db.query(SocialMetric).filter_by(symbol=symbol, date=row['date']).first()
            if not existing:
                metric = SocialMetric(
                    symbol=symbol,
                    date=row['date'],
                    mentions=row['mentions'],
                    bullish_pct=row['bullish_pct'],
                    bearish_pct=row['bearish_pct'],
                    neutral_pct=row['neutral_pct']
                )
                db.add(metric)
    db.commit()

def get_daily_sentiment_trend(db: Session, symbol: str, days_back: int = 7) -> Optional[Dict]:
    """Query DB for daily counters + live (latest). Returns avg sentiment, mention growth."""
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_back)
    metrics = db.query(SocialMetric).filter(
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
        'neutral_pct': m.neutral_pct
    } for m in metrics])
    
    # Daily counters: Sum/avg per day
    daily = df.groupby('date').agg({
        'mentions': 'sum',
        'bullish_pct': 'mean',
        'bearish_pct': 'mean',
        'neutral_pct': 'mean'
    }).reset_index()
    
    # Live current 24h: Latest row
    live = daily.iloc[-1].to_dict()
    
    # Trend: Mention growth % (current vs prev day)
    if len(daily) > 1:
        growth = (live['mentions'] - daily.iloc[-2]['mentions']) / daily.iloc[-2]['mentions'] * 100 if daily.iloc[-2]['mentions'] > 0 else 0
        live['mention_growth_pct'] = growth
    else:
        live['mention_growth_pct'] = 0
    
    live['net_sentiment'] = live['bullish_pct'] - live['bearish_pct']  # Simple score
    
    return {'daily_history': daily.to_dict('records'), 'live_24h': live}

# Scheduler integration (in main.py)
def update_sentiment_job():
    """Run daily/hourly: Fetch and store."""
    from db.utils import get_db
    db = next(get_db())
    try:
        top_symbols = fetch_top_50_coins()
        metrics = fetch_sentiment_time_series(top_symbols)
        store_metrics(db, metrics)
        print(f"Updated sentiment for {len(top_symbols)} top coins.")
    except Exception as e:
        print(f"Sentiment update failed: {e}")

# FastAPI endpoint (in routes.py)
from fastapi import APIRouter, Depends
router = APIRouter()

@router.get('/top-sentiment')
def get_top_sentiment(db=Depends(get_db)):
    top_symbols = fetch_top_50_coins()  # Or cache
    trends = {}
    for sym in top_symbols[:10]:  # Limit for demo; full in prod
        trend = get_daily_sentiment_trend(db, sym)
        if trend:
            trends[sym] = trend['live_24h']
    return {'top_50_sentiment': trends}  # For dashboard

@router.get('/sentiment/{symbol}')
def get_sentiment(symbol: str, db=Depends(get_db)):
    trend = get_daily_sentiment_trend(db, symbol)
    return trend or {'error': 'No data'}