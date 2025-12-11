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