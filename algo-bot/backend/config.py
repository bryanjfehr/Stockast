# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
MEXC_API_KEY = os.getenv("MEXC_API_KEY")
MEXC_API_SECRET = os.getenv("MEXC_API_SECRET")

# API Configuration
MEXC_API_BASE = "https://api.mexc.com"  # Base URL for MEXC public API endpoints

# Database
DB_FILE = "bot.db"

# Trading parameters (for single-symbol testing; scanning uses all symbols)
SYMBOL = "BTCUSDT"  # Note: Use MEXC format (no underscore)
TIMEFRAME = "1h"

# Scanning parameters (for batch processing in main.py)
SCAN_BATCH_SIZE = 100  # Symbols per batch to respect rate limits
SCAN_INTERVAL = 5    # Seconds between batches
MAX_KLINES_FAILURES = 5 # Max consecutive kline fetch failures before a symbol is marked inactive
KLINE_HISTORY_DAYS = 30 # How many days of kline data to keep in the database
MOMENTUM_PERIODS = 10 # For ROC calculation

# --- DB Column Definitions ---
DB_COLS_1H = [
    'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume',
    'ma_10', 'ma_50', 'rsi_14', 'macd', 'macd_signal', 'macd_hist',
    'volume_spike', 'vol_ratio_5', 'vol_ratio_10', 'volatility_5m', 'volatility_1h', 
    'hourly_trend', 'prob_score'
]
DB_COLS_15M = DB_COLS_1H + ['momentum_roc']
DB_COLS_5M = [
    'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume',
    'ma_10', 'ma_50', 'rsi_14', 'macd', 'macd_signal', 'macd_hist',
    'volume_spike', 'vol_ratio_5', 'vol_ratio_10', 'volatility_5m', 'volatility_1h',
    'hourly_trend', 'prob_score', 'momentum_roc'
]

VOLUME_THRESHOLD = 100000  # Min $100k 24hr volume filter
STRATEGY = 'HIGH_CONFIDENCE'  # Default strategy name