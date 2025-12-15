# db.py
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import List, Any, Dict, Optional
from config import DB_FILE, MAX_KLINES_FAILURES
from api import api

logger = logging.getLogger(__name__)

def connect_db():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

def create_tables():
    """Creates the necessary database tables if they don't exist."""
    conn = connect_db()
    conn.execute("PRAGMA foreign_keys = ON") # Enable foreign key support
    cursor = conn.cursor()

    # Raw Klines table (for all intervals)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_klines (
            symbol TEXT,
            interval TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            close_time INTEGER,
            quote_volume REAL,
            PRIMARY KEY (symbol, interval, timestamp)
        )
    """)
    # Symbols table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS symbols (
            symbol TEXT PRIMARY KEY,
            base_asset TEXT,
            quote_asset TEXT,
            status TEXT,
            date_added DATETIME,
            is_active BOOLEAN,
            klines_fail_count INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klines_1h (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            close_time INTEGER,
            quote_volume REAL,
            ma_10 REAL,
            ma_50 REAL,
            rsi_14 REAL,
            macd REAL,
            macd_signal REAL,
            macd_hist REAL,
            volume_spike INTEGER DEFAULT 0,
            vol_ratio_5 REAL DEFAULT 0,
            vol_ratio_10 REAL DEFAULT 0,
            volatility_5m REAL DEFAULT 0,
            volatility_1h REAL DEFAULT 0,
            hourly_trend REAL DEFAULT 0,
            prob_score REAL DEFAULT 0,
            atr REAL DEFAULT 0,
            adx REAL DEFAULT 0,
            UNIQUE(symbol, timestamp),
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    # New 15m table (similar schema, but vol/volatility tuned for shorter TF)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klines_15m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL, close_time INTEGER, quote_volume REAL,
            ma_10 REAL, ma_50 REAL, rsi_14 REAL, macd REAL, macd_signal REAL, macd_hist REAL,
            volume_spike INTEGER DEFAULT 0, vol_ratio_5 REAL DEFAULT 0, vol_ratio_10 REAL DEFAULT 0,
            volatility_5m REAL DEFAULT 0, volatility_1h REAL DEFAULT 0, hourly_trend REAL DEFAULT 0,
            prob_score REAL DEFAULT 0, momentum_roc REAL DEFAULT 0,
            UNIQUE(symbol, timestamp),
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    # New 5m table (short-term focus: momentum, volatility)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klines_5m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL, volume REAL, close_time INTEGER, quote_volume REAL,
            ma_10 REAL, ma_50 REAL, rsi_14 REAL, macd REAL, macd_signal REAL, macd_hist REAL,
            volume_spike INTEGER DEFAULT 0, vol_ratio_5 REAL DEFAULT 0, vol_ratio_10 REAL DEFAULT 0,
            volatility_5m REAL DEFAULT 0, volatility_1h REAL DEFAULT 0, hourly_trend REAL DEFAULT 0,
            prob_score REAL DEFAULT 0, momentum_roc REAL DEFAULT 0,
            UNIQUE(symbol, timestamp),
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    # New sentiment daily table
    create_sentiment_table()

    # Top symbols snapshot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS top_symbols_1h (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER, -- Store as INTEGER (Unix timestamp in ms)
            symbol TEXT,
            prob_score REAL,
            rank INTEGER,
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    # Signals table to log potential buys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            signal_price REAL,
            signal_time INTEGER, -- Store as INTEGER (Unix timestamp in ms)
            volume_at_signal REAL,
            strategy TEXT,
            status TEXT DEFAULT 'NEW',
            rsi REAL,
            ma_diff_pct REAL,
            prob_score REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            active_indicators TEXT DEFAULT '',
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    # Strategies table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            min_signals INTEGER DEFAULT 3,
            prob_threshold REAL DEFAULT 0.6,
            thresholds TEXT,
            risk_level TEXT DEFAULT 'MEDIUM'
        )
    ''')

    # Positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            entry_price REAL,
            quantity REAL, -- Amount of base asset bought
            stop_loss REAL,
            take_profit REAL,
            status TEXT,
            entry_time INTEGER, -- Unix timestamp in ms
            exit_time INTEGER, -- Unix timestamp in ms
            pnl_pct REAL, -- Percentage profit/loss
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    # Long-term klines table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS long_term_klines (
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,  -- '1d', '1h', '4h'
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (symbol, interval, timestamp)
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_interval ON long_term_klines (symbol, interval)
    ''')
    
    conn.commit()
    conn.close()
    seed_strategies()  # Seed the strategies table with default values
    logger.info("Database tables created successfully.")

def create_sentiment_table():
    """Creates the sentiment_daily table if it doesn't exist."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_daily (
            symbol TEXT, date TEXT, social_volume REAL, sentiment_balance REAL,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Sentiment daily table created successfully.")

def get_db_table_name_for_interval(interval: str, is_raw: bool = False) -> str:
    """Maps an interval string to its corresponding database table name."""
    if is_raw:
        return "raw_klines"
    
    # Map API intervals to internal DB table names for enriched data
    if interval == '60m' or interval == '1h':
        return "klines_1h"
    elif interval == '15m':
        return "klines_15m"
    elif interval == '5m':
        return "klines_5m"
    # Add other enriched tables if they are created (e.g., klines_1d for enriched daily)
    else:
        raise ValueError(f"Unsupported interval for enriched data: {interval}")

def seed_strategies():
    """Seeds the strategies table with some default configurations."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Removed duplicate signals table creation.
        # Ensure the strategies table exists before seeding
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, description TEXT, min_signals INTEGER DEFAULT 3, prob_threshold REAL DEFAULT 0.6, thresholds TEXT, risk_level TEXT DEFAULT 'MEDIUM'
            )
        ''')
        strategies_to_insert = [
            ('HIGH_CONFIDENCE', 'Stricter with momentum/trend', 3, 0.4, '{"rsi_oversold": 35, "vol_mult": 2.0, "vol_spike": true, "trend_min": 0.5, "momentum_min": 0, "adx_threshold": 25}', 'LOW'),
            ('BALANCED', 'Balanced with momentum', 3, 0.5, '{"rsi_oversold": 40, "vol_mult": 1.8, "vol_spike": true, "trend_min": 0.3, "momentum_min": -0.5, "adx_threshold": 25}', 'MEDIUM'),
            ('AGGRESSIVE', 'Aggressive with light momentum', 3, 0.4, '{"rsi_oversold": 45, "vol_mult": 1.5, "vol_spike": true, "trend_min": 0.1, "momentum_min": -1.0, "adx_threshold": 25}', 'HIGH')
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO strategies (name, description, min_signals, prob_threshold, thresholds, risk_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', strategies_to_insert)
        conn.commit()
        logger.info("Seeded strategies with tuned params.")
    finally:
        conn.close()
        
def init_symbols_db():
    """
    Initializes/updates the symbols table from the MEXC API.
    Marks existing symbols as inactive, then updates them or adds new ones.
    """
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Mark all existing symbols as inactive
        cursor.execute('UPDATE symbols SET is_active = 0')
        data = api.get_exchange_info()

        api_symbols = []
        for sym in data.get('symbols', []):
            # According to mexc_api_info.txt, status '1' means online.
            if (sym.get('isSpotTradingAllowed') and sym.get('quoteAsset') == 'USDT' and sym.get('status') == '1'):
                api_symbols.append({
                    'symbol': sym['symbol'],
                    'base_asset': sym['baseAsset'],
                    'quote_asset': sym['quoteAsset'],
                    'status': sym['status'],
                    'date_added': datetime.now(timezone.utc),
                    'is_active': 1
                })
        
        if api_symbols:
            # Use INSERT...ON CONFLICT for an efficient "upsert".
            # This inserts a new symbol, or if it exists, updates its is_active status.
            cursor.executemany('''
                INSERT INTO symbols (symbol, base_asset, quote_asset, status, date_added, is_active)
                VALUES (:symbol, :base_asset, :quote_asset, :status, :date_added, :is_active)
                ON CONFLICT(symbol) DO UPDATE SET
                    is_active = excluded.is_active
            ''', api_symbols)

            conn.commit()
            logger.info(f"Successfully upserted {len(api_symbols)} symbols from API.")


    except (ValueError) as e:
        logger.error(f"Error fetching symbols from MEXC API: {e}")
    finally:
        conn.close()

def get_all_symbols():
    """Retrieves all active symbols from the database."""
    conn = connect_db()
    cursor = conn.cursor()
    # Filter out symbols that have failed kline fetches too many times
    cursor.execute("SELECT symbol FROM symbols WHERE is_active = 1 AND klines_fail_count < ?", (MAX_KLINES_FAILURES,))
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols

def save_raw_klines(symbol: str, interval: str, klines_data: List[tuple]):
    """Saves a list of raw klines to the raw_klines table, ignoring duplicates."""
    if not klines_data:
        return

    table_name = get_db_table_name_for_interval(interval, is_raw=True) # "raw_klines"
    cols = ['symbol', 'interval', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume']
    placeholders = ','.join(['?' for _ in cols])
    insert_sql = f'''
        INSERT OR IGNORE INTO {table_name} ({','.join(cols)})
        VALUES ({placeholders})
    '''
    
    data_to_insert = [
        (symbol, interval, int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), int(k[6]), float(k[7]))
        for k in klines_data
    ]

    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.executemany(insert_sql, data_to_insert)
        conn.commit()
        logger.debug(f"Saved {cursor.rowcount} raw {interval} klines for {symbol}.")
    except sqlite3.Error as e:
        logger.error(f"DB error saving raw {interval} klines for {symbol}: {e}")
    finally:
        conn.close()

def fetch_raw_klines(symbol: str, interval: str, start_ts: int, end_ts: int) -> List[tuple]:
    """Fetches raw klines from the raw_klines table within a specified time range."""
    table_name = get_db_table_name_for_interval(interval, is_raw=True) # "raw_klines"
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT timestamp, open, high, low, close, volume, close_time, quote_volume 
            FROM {table_name} 
            WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (symbol, interval, start_ts, end_ts))
        return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"DB error fetching raw {interval} klines for {symbol}: {e}")
        return []
    finally:
        conn.close()

def save_long_term_klines(symbol: str, interval: str, klines_data: List[tuple]):
    """Saves a list of klines to the long_term_klines table, ignoring duplicates."""
    if not klines_data:
        return

    # The klines_data from get_historical_data has 8 columns:
    # timestamp, open, high, low, close, volume, close_time, quote_volume
    # The long_term_klines table expects 8 columns:
    # symbol, interval, timestamp, open, high, low, close, volume
    data_to_insert = [
        (symbol, interval, int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
        for k in klines_data
    ]

    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.executemany("""
            INSERT OR IGNORE INTO long_term_klines (symbol, interval, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data_to_insert)
        conn.commit()
        logger.info(f"Saved/updated {cursor.rowcount} records in long_term_klines for {symbol} {interval}.")
    except sqlite3.Error as e:
        logger.error(f"DB error saving to long_term_klines for {symbol}: {e}")
    finally:
        conn.close()

def save_sentiment_daily_data(symbol: str, df: pd.DataFrame):
    """Saves daily sentiment data to the database."""
    if df.empty:
        return
    
    # Ensure 'date' column is in 'YYYY-MM-DD' format for the TEXT PRIMARY KEY
    # Assuming df has 'datetime', 'social_volume', 'sentiment_balance'
    df['date'] = df['datetime'].dt.strftime('%Y-%m-%d')
    df_to_save = df[['symbol', 'date', 'social_volume', 'sentiment_balance']]
    
    conn = connect_db()
    try:
        # Use to_sql with if_exists='append' and the PRIMARY KEY constraint
        # will handle upserting (inserting new or ignoring existing)
        df_to_save.to_sql('sentiment_daily', conn, if_exists='append', index=False)
        logger.debug(f"Saved {len(df_to_save)} sentiment records for {symbol}.")
    except sqlite3.Error as e:
        logger.error(f"DB error saving sentiment data for {symbol}: {e}")
    finally:
        conn.close()

def get_sentiment_daily_data(symbol: str, days_back: int) -> pd.DataFrame:
    """Retrieves daily sentiment data for a symbol from the database."""
    conn = connect_db()
    try:
        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')
        query = """
            SELECT date, social_volume, sentiment_balance
            FROM sentiment_daily
            WHERE symbol = ? AND date >= ?
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn, params=(symbol, from_date))
        df['date'] = pd.to_datetime(df['date'])
        df.rename(columns={'date': 'datetime'}, inplace=True) # Rename back to datetime for consistency with san.get output
        return df
    except sqlite3.Error as e:
        logger.error(f"DB error retrieving sentiment data for {symbol}: {e}")
        return pd.DataFrame()
    finally:
        conn.close()
def increment_klines_fail_count(symbol: str):
    """
    Increments the klines_fail_count for a given symbol.
    If count exceeds MAX_KLINES_FAILURES, marks symbol as inactive.
    """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE symbols SET klines_fail_count = klines_fail_count + 1 WHERE symbol = ?", (symbol,))
        cursor.execute("SELECT klines_fail_count FROM symbols WHERE symbol = ?", (symbol,))
        current_count = cursor.fetchone()[0]
        if current_count >= MAX_KLINES_FAILURES:
            cursor.execute("UPDATE symbols SET is_active = 0 WHERE symbol = ?", (symbol,))
            logger.warning(f"Symbol {symbol} marked as inactive due to {MAX_KLINES_FAILURES} kline fetch failures.")
        conn.commit()
        logger.debug(f"Incremented klines_fail_count for {symbol} to {current_count}.")
    except sqlite3.Error as e:
        logger.error(f"Database error incrementing klines_fail_count for {symbol}: {e}")
    finally:
        conn.close()

def reset_klines_fail_count(symbol: str):
    """Resets the klines_fail_count for a given symbol to 0."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE symbols SET klines_fail_count = 0 WHERE symbol = ?", (symbol,))
        conn.commit()
        logger.debug(f"Reset klines_fail_count for {symbol}.")
    except sqlite3.Error as e:
        logger.error(f"Database error resetting klines_fail_count for {symbol}: {e}")
    finally:
        conn.close()

def save_klines_by_interval(interval: str, enriched_klines: List[tuple], cols: List[str]):
    """
    Saves enriched klines to a timeframe-specific table.
    """
    if not enriched_klines:
        return
    
    table_name = f'klines_{interval}'
    placeholders = ','.join(['?' for _ in cols])
    insert_sql = f'''
        INSERT OR IGNORE INTO {table_name} ({','.join(cols)})
        VALUES ({placeholders})
    '''
    
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.executemany(insert_sql, enriched_klines)
        conn.commit()
        logger.debug(f"Upserted {cursor.rowcount} {interval} klines.")
    except sqlite3.Error as e:
        logger.error(f"DB error saving {interval} klines: {e}")
    finally:
        conn.close()

def save_signal(symbol: str, price: float, volume: float, strategy: str, metrics: Dict[str, Any] = None, 
                active_indicators: List[str] = None, prob_score: float = 0.0, confidence: float = 0.0):
    """Saves a detected buy signal to the database, including optional metrics."""
    conn = connect_db()
    cursor = conn.cursor()
    metrics = metrics or {}
    rsi = metrics.get('rsi')
    ma_diff_pct = metrics.get('ma_diff_pct')
    indicators_str = ','.join(active_indicators) if active_indicators else '' # Changed from signal_time DATETIME to INTEGER
    signal_time = datetime.now(timezone.utc)

    try:
        cursor.execute('''
            INSERT INTO signals (symbol, signal_price, signal_time, volume_at_signal, strategy, 
                                rsi, ma_diff_pct, prob_score, confidence, active_indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, price, signal_time, volume, strategy, rsi, ma_diff_pct, prob_score, confidence, indicators_str))
        conn.commit()
        logger.info(f"Saved signal for {symbol} (ID: {cursor.lastrowid}).")
    except sqlite3.Error as e:
        logger.error(f"Database error while saving signal for {symbol}: {e}")
    finally:
        conn.close()

def prune_old_klines(days_to_keep: int):
    """
    Removes kline data older than a specified number of days from all kline tables.
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    # Timestamps in the DB are in milliseconds
    cutoff_timestamp_ms = int(cutoff_date.timestamp() * 1000)
    tables_to_prune = ['klines_1h', 'klines_15m', 'klines_5m']
    total_deleted = 0

    try:
        logger.info(f"Pruning kline data older than {days_to_keep} days (before {cutoff_date.strftime('%Y-%m-%d')})...")
        for table in tables_to_prune:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff_timestamp_ms,))
                rows_deleted = cursor.rowcount
                if rows_deleted > 0:
                    logger.debug(f"Pruned {rows_deleted} records from {table}.")
                total_deleted += rows_deleted
            except sqlite3.OperationalError as e:
                if "no such table" in str(e).lower():
                    logger.debug(f"Table '{table}' not found for pruning, skipping.")
                else:
                    raise e
        if total_deleted > 0:
            conn.commit()
            logger.info(f"Successfully pruned {total_deleted} old kline records in total.")
        else:
            logger.info("Pruning complete. No old records found to delete.")
    except sqlite3.Error as e:
        logger.error(f"Database error while pruning klines: {e}")
    finally:
        conn.close()

def get_active_symbols_with_history(min_hours: int = 200, interval: str = '1h'):
    """Get symbols with >= min_hours klines."""
    table = f'klines_{interval}'
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # This ensures the table exists before querying.
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone() is None:
            logger.warning(f"Table {table} does not exist. Cannot get symbols with history.")
            return []

        cursor.execute(f'''
            SELECT DISTINCT s.symbol FROM symbols s
            INNER JOIN {table} k ON s.symbol = k.symbol
            WHERE s.is_active = 1 AND s.klines_fail_count < ?
            GROUP BY s.symbol HAVING COUNT(k.timestamp) >= ?
        ''', (MAX_KLINES_FAILURES, min_hours))
        symbols = [row[0] for row in cursor.fetchall()]
        return symbols
    finally:
        conn.close()

def insert_top_symbols(top_list: List[Dict[str, Any]]):
    """top_list: [{'symbol': 'BTCUSDT', 'prob_score': 0.85, 'rank': 1}, ...]"""
    conn = connect_db()
    cursor = conn.cursor()
    ts = datetime.now(timezone.utc)
    data = [(ts, item['symbol'], item['prob_score'], item['rank']) for item in top_list]
    try:
        cursor.executemany('''
            INSERT INTO top_symbols_1h (timestamp, symbol, prob_score, rank)
            VALUES (?, ?, ?, ?)
        ''', data)
        conn.commit()
        logger.info(f"Inserted top {len(top_list)} symbols snapshot.")
        # Prune old snapshots (keep last 24h)
        cutoff = ts - timedelta(hours=24)
        cursor.execute("DELETE FROM top_symbols_1h WHERE timestamp < ?", (cutoff,))
        conn.commit()
    finally:
        conn.close()

def get_strategy_config(strategy_name: str):
    """Fetch strategy row as dict."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Makes rows dict-like
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM strategies WHERE name = ?", (strategy_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)  # Now proper dict
    return None

def get_latest_top_symbols(n: int = 100) -> List[Dict[str, Any]]:
    """Return list of dicts from latest snapshot."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT symbol, prob_score, rank FROM top_symbols_1h
        WHERE timestamp = (SELECT MAX(timestamp) FROM top_symbols_1h)
        ORDER BY rank ASC LIMIT ?
    ''', (n,))
    symbols = [{'symbol': row[0], 'prob_score': row[1], 'rank': row[2]} for row in cursor.fetchall()]
    conn.close()
    return symbols