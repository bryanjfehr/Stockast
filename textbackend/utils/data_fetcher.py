import logging
import ccxt
import time
import pandas as pd
from db.utils import store_data
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

def fetch_symbols(exchange):
    """
    Fetches all symbols from the exchange.
    """
    try:
        markets = exchange.load_markets()
        return list(markets.keys())
    except (ccxt.ExchangeError, ccxt.NetworkError) as e:
        print(f"Error fetching symbols: {e}")
        return []

def fetch_ohlcv(exchange, symbol, timeframe='1h', limit=1000):
    """
    Fetches OHLCV data for a given symbol and timeframe.
    """
    if not exchange.has['fetchOHLCV']:
        print(f"{exchange.id} does not support fetchOHLCV.")
        return pd.DataFrame()

    try:
        # Respect rate limit
        time.sleep(exchange.rateLimit / 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # store_data(df, f'{symbol}_{timeframe}_ohlcv') # Placeholder for storing data
        return df
    except (ccxt.ExchangeError, ccxt.NetworkError) as e:
        print(f"Error fetching OHLCV for {symbol}: {e}")
        return pd.DataFrame()

def fetch_order_book(exchange, symbol, limit=20):
    """
    Fetches the order book for a given symbol.
    """
    if not exchange.has['fetchOrderBook']:
        print(f"{exchange.id} does not support fetchOrderBook.")
        return None

    try:
        # Respect rate limit
        time.sleep(exchange.rateLimit / 1000)
        order_book = exchange.fetch_order_book(symbol, limit=limit)
        return order_book
    except (ccxt.ExchangeError, ccxt.NetworkError) as e:
        print(f"Error fetching order book for {symbol}: {e}")
        return None

def fetch_multi_histories(symbols: List[str], exchange: ccxt.Exchange, timeframe='1h', days_back=365) -> Dict[str, pd.DataFrame]:
    """
    Fetches historical OHLCV data for multiple symbols in parallel.

    Args:
        symbols: List of symbols to fetch data for.
        exchange: A ccxt exchange instance.
        timeframe: The timeframe to fetch data for (e.g., '1h', '4h', '1d').
        days_back: The number of days of historical data to fetch.

    Returns:
        A dictionary where keys are symbols and values are pandas DataFrames
        with OHLCV data and calculated indicators.
    """
    histories = {}
    since = exchange.parse8601((datetime.utcnow() - timedelta(days=days_back)).isoformat())

    def fetch_history(symbol):
        logging.info(f"Fetching history for {symbol}...")
        for i in range(3):  # Retry up to 3 times
            try:
                time.sleep(exchange.rateLimit / 1000)  # Respect rate limit
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                # Calculate percentage changes
                df['change_pct'] = df['close'].pct_change()
                df['volume_pct'] = df['volume'].pct_change()
                
                # Volatility (e.g., standard deviation of log returns)
                df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
                df['volatility_pct'] = df['log_ret'].rolling(window=20).std()

                # Placeholder for sentiment
                df['sentiment_pct'] = 0.5  # Neutral sentiment

                df.dropna(inplace=True)
                logging.info(f"Successfully fetched history for {symbol}.")
                return symbol, df
            except (ccxt.ExchangeError, ccxt.NetworkError) as e:
                logging.error(f"Error fetching {symbol} (attempt {i+1}): {e}")
                time.sleep(5)  # Wait before retrying
        return symbol, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_history, symbols)

    for symbol, df in results:
        if df is not None and not df.empty:
            histories[symbol] = df
            
    return histories

# WebSocket for real-time k-lines (placeholder)
# This would require a library like 'websockets' and an async implementation.
# async def subscribe_to_klines(symbol, timeframe):
#     # Implementation-specific details for the exchange's WebSocket API
#     pass