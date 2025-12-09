import logging
import ccxt
import pandas as pd
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory cache for exchange info to avoid frequent API calls
_exchange_info_cache = None
_exchange_instance = None

def fetch_exchange_info(refresh: bool = False) -> Dict:
    """
        A dictionary containing exchange information.
    """
    global _exchange_info_cache, _exchange_instance
    if _exchange_instance is None:
        _exchange_instance = ccxt.mexc({'enableRateLimit': True})

    if _exchange_info_cache is None or refresh:
        try:
            logging.info("Fetching exchange info...")
            _exchange_info_cache = _exchange_instance.load_markets()
            logging.info("Successfully fetched and cached new exchange info.")
        except Exception as e:
            logging.error(f"Failed to fetch exchange info: {e}")
            return {}
    else:
        logging.info("Using cached exchange info.")
    return _exchange_info_cache

def get_top_symbols(exchange: ccxt.Exchange, limit: int = 50) -> List[str]:
    """Fetch top spot symbols by quote volume (USDT pairs for diversity)."""
    try:
        logging.info(f"Fetching top {limit} symbols by quote volume...")

        # fetch_tickers() retrieves 24hr stats for all symbols when called without arguments.
        # This corresponds to the documented GET /api/v3/ticker/24hr endpoint and avoids
        # the problematic load_markets() call that was causing permission errors.
        all_tickers = exchange.fetch_tickers()

        if not all_tickers:
            logging.error("exchange.fetch_tickers() returned no data. Check API key permissions for ticker endpoints.")
            return []
        
        # Filter tickers that are USDT spot pairs and have quoteVolume
        # The 'symbol' format (e.g., 'BTC/USDT') is a strong indicator of a spot market.
        valid_tickers = [
            (symbol, ticker['quoteVolume'])
            for symbol, ticker in all_tickers.items()
            if symbol.endswith('/USDT') and '/' in symbol and ticker.get('quoteVolume') is not None
        ]
        
        if not valid_tickers:
            logging.warning("Could not find any valid USDT spot tickers with quoteVolume from the fetched tickers.")
            return []

        sorted_pairs = sorted(valid_tickers, key=lambda x: x[1], reverse=True)

        top_symbols = [p[0] for p in sorted_pairs[:limit]]
        logging.info(f"Successfully identified {len(top_symbols)} top symbols.")
        return top_symbols
    except Exception as e:
        logging.error(f"Failed to get top symbols: {e}", exc_info=True)
        return []

def fetch_one_history(sym: str, exchange: Any, days_back: int = 365, timeframe='1h', limit=1000) -> Optional[pd.DataFrame]:
    """
    Fetches OHLCV history for a single symbol.
    
    Args:
        sym (str): The symbol to fetch.
        exchange (ccxt.Exchange): The ccxt exchange instance.
        days_back (int): How many days of history to retrieve.
        timeframe (str): The timeframe to fetch (e.g., '1h', '1d').
        limit (int): The number of candles to fetch per request.
    """
    logging.debug(f"Fetching history for {sym} with timeframe {timeframe} for {days_back} days...")
    since = int((pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days_back)).timestamp() * 1000)
    try:
        ohlcv = exchange.fetch_ohlcv(sym, timeframe, since=since, limit=limit)
        if not ohlcv:
            logging.warning(f"No OHLCV data returned for {sym}.")
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logging.error(f"Failed to fetch history for {sym}: {e}")
        return None

def fetch_multi_histories(exchange: ccxt.Exchange, symbols: List[str], timeframe: str = '1h', days_back: int = 365) -> Dict[str, pd.DataFrame]:
    """
    Fetches historical data for multiple symbols in parallel.

    Args:
        exchange (ccxt.Exchange): An authenticated ccxt exchange instance.
        symbols (List[str]): A list of symbols to fetch.
        timeframe (str): The timeframe for the data (e.g., '1h', '1d').
        days_back (int): How many days of history to retrieve.

    Returns:
        A dictionary mapping symbols to their historical data as DataFrames.
    """
    logging.info(f"Initiating parallel fetch for {len(symbols)} symbols using provided exchange client...")
    histories = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Map each symbol to a future
        future_to_symbol = {executor.submit(fetch_one_history, sym, exchange, days_back, timeframe): sym for sym in symbols}
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    histories[symbol] = df
            except Exception as exc:
                logging.error(f'{symbol} generated an exception: {exc}')
    
    logging.info(f"Successfully fetched histories for {len(histories)} out of {len(symbols)} symbols.")
    return histories
