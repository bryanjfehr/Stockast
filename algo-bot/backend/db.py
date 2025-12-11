# db.py
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Any, Dict
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

    # Klines table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klines (
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
            ma_30 REAL,
            ma_60 REAL,
            ma_200 REAL,
            rsi_6 REAL,
            rsi_12 REAL,
            rsi_24 REAL,
            macd REAL,
            macd_signal REAL,
            macd_hist REAL,
            macd_slope TEXT,
            kdj_k REAL,
            kdj_d REAL,
            kdj_j REAL,
            fib_382 REAL,
            fib_618 REAL,
            fib_50 REAL,
            UNIQUE(symbol, timestamp),
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
            active_indicators TEXT DEFAULT '',
            FOREIGN KEY (symbol) REFERENCES symbols (symbol)
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
    logger.info("Database tables created successfully.")

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

def save_klines(enriched_klines: List[tuple]):
    """
    Saves a list of klines with calculated indicators to the database.
    Uses INSERT OR IGNORE to avoid duplicates.
    The first element of each tuple in enriched_klines must be the symbol.
    """
    if not enriched_klines:
        return

    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.executemany('''
            INSERT OR IGNORE INTO klines (
                symbol, timestamp, open, high, low, close, volume, close_time, quote_volume,
                ma_10, ma_30, ma_60, ma_200, rsi_6, rsi_12, rsi_24,
                macd, macd_signal, macd_hist, macd_slope,
                kdj_k, kdj_d, kdj_j,
                fib_382, fib_618, fib_50
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', enriched_klines)
        conn.commit()
        if cursor.rowcount > 0:
            # Log is now less specific as symbol is part of the tuple list
            logger.debug(f"Upserted {cursor.rowcount} new klines into the database.")
    except sqlite3.Error as e:
        logger.error(f"Database error while saving klines: {e}")
    finally:
        conn.close()

def save_signal(symbol: str, price: float, volume: float, strategy: str, metrics: Dict[str, Any] = None, active_indicators: List[str] = None):
    """Saves a detected buy signal to the database, including optional metrics."""
    conn = connect_db()
    cursor = conn.cursor()
    metrics = metrics or {}
    rsi = metrics.get('rsi')
    ma_diff_pct = metrics.get('ma_diff_pct')
    indicators_str = ','.join(active_indicators) if active_indicators else ''

    try:
        cursor.execute('''
            INSERT INTO signals (symbol, signal_price, signal_time, volume_at_signal, strategy, rsi, ma_diff_pct, active_indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, price, datetime.utcnow(), volume, strategy, rsi, ma_diff_pct, indicators_str))
        conn.commit()
        # The previous log is now handled in main.py after the call
    except sqlite3.Error as e:
        logger.error(f"Database error while saving signal for {symbol}: {e}")
    finally:
        conn.close()

def prune_old_klines(days_to_keep: int):
    """
    Removes kline data older than a specified number of days to keep the DB size manageable.
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    # Timestamps in the DB are in milliseconds
    cutoff_timestamp_ms = int(cutoff_date.timestamp() * 1000)
    
    try:
        logger.info(f"Pruning kline data older than {days_to_keep} days (before {cutoff_date.strftime('%Y-%m-%d')})...")
        cursor.execute("DELETE FROM klines WHERE timestamp < ?", (cutoff_timestamp_ms,))
        
        rows_deleted = cursor.rowcount
        conn.commit()
        
        logger.info(f"Successfully pruned {rows_deleted} old kline records.")
    except sqlite3.Error as e:
        logger.error(f"Database error while pruning klines: {e}")
    finally:
        conn.close()
