# db.py
import sqlite3
import logging
from datetime import datetime, timedelta
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
    cursor = conn.cursor()

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

    # Top symbols snapshot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS top_symbols_1h (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
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
            signal_time DATETIME,
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
            quantity REAL,
            stop_loss REAL,
            take_profit REAL,
            status TEXT,
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
        )
    ''')

    conn.commit()
    conn.close()
    seed_strategies() # Seed the strategies table with default values
    logger.info("Database tables created successfully.")

def seed_strategies():
    """Seeds the strategies table with some default configurations."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        strategies_to_insert = [
            ('HIGH_CONFIDENCE', '4 signals, high probability, low risk', 4, 0.7, '{"rsi_oversold": 30, "vol_mult": 2.0, "vol_spike": true}', 'LOW'),
            ('BALANCED', '3 signals, medium probability, medium risk', 3, 0.5, '{"rsi_oversold": 40, "vol_mult": 1.5}', 'MEDIUM'),
            ('AGGRESSIVE', '2 signals, lower probability, high risk', 2, 0.3, '{"rsi_oversold": 50, "vol_mult": 1.2}', 'HIGH')
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO strategies (name, description, min_signals, prob_threshold, thresholds, risk_level)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', strategies_to_insert)
        conn.commit()
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
                    'date_added': datetime.utcnow(),
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
    indicators_str = ','.join(active_indicators) if active_indicators else ''
    signal_time = datetime.utcnow()

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
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
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
    ts = datetime.utcnow()
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