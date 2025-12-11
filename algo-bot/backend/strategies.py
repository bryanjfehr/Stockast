# strategies.py
import pandas as pd
import pandas_ta as ta  # For technical indicators
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

def calculate_and_enrich_klines(symbol: str, klines: List[List[str]]) -> List[tuple]:
    """
    Takes raw kline data, calculates a suite of technical indicators (incl. Fib),
    and returns a list of tuples ready for database insertion.
    """
    if not klines:
        return []

    # Create a DataFrame with all original columns
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'
    ])
    
    # Convert to numeric, coercing errors
    numeric_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Calculate Indicators using pandas-ta ---
    # Moving Averages
    df['ma_10'] = ta.sma(df['close'], length=10)
    df['ma_30'] = ta.sma(df['close'], length=30)
    df['ma_60'] = ta.sma(df['close'], length=60)
    df['ma_200'] = ta.sma(df['close'], length=200)  # For Fib uptrend filter

    # RSI
    df['rsi_6'] = ta.rsi(df['close'], length=6)
    df['rsi_12'] = ta.rsi(df['close'], length=12)
    df['rsi_24'] = ta.rsi(df['close'], length=24)

    # MACD
    macd_df = ta.macd(df['close'])
    if macd_df is not None and not macd_df.empty:
        df['macd'] = macd_df.iloc[:, 0]
        df['macd_hist'] = macd_df.iloc[:, 1]
        df['macd_signal'] = macd_df.iloc[:, 2]

    # MACD Slope
    df['macd_slope'] = 'flat'  # Default
    df.loc[df['macd_hist'] > df['macd_hist'].shift(1), 'macd_slope'] = 'positive'
    df.loc[df['macd_hist'] < df['macd_hist'].shift(1), 'macd_slope'] = 'negative'

    # KDJ
    kdj_df = ta.kdj(df['high'], df['low'], df['close'])
    if kdj_df is not None and not kdj_df.empty:
        df['kdj_k'] = kdj_df.iloc[:, 0]
        df['kdj_d'] = kdj_df.iloc[:, 1]
        df['kdj_j'] = kdj_df.iloc[:, 2]

    # Fibonacci Retracement Levels (rolling over last 20 periods)
    lookback = 20
    def compute_fib(row_idx):
        if row_idx < lookback:
            return None, None, None
        window = df.iloc[row_idx - lookback + 1 : row_idx + 1]
        high = window['high'].max()
        low = window['low'].min()
        diff = high - low
        fib_382 = high - (diff * 0.382)  # Common entry level
        fib_618 = high - (diff * 0.618)
        return fib_382, fib_618, (high + low) / 2  # 50% for reference
    fibs = [compute_fib(i) for i in range(len(df))]
    df['fib_382'], df['fib_618'], df['fib_50'] = zip(*fibs) if fibs else ([None] * len(df), [None] * len(df), [None] * len(df))

    # --- Prepare for Database Insertion ---
    df['symbol'] = symbol
    df.replace({np.nan: None}, inplace=True)

    db_columns = [
        'symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume',
        'ma_10', 'ma_30', 'ma_60', 'ma_200', 'rsi_6', 'rsi_12', 'rsi_24',
        'macd', 'macd_signal', 'macd_hist', 'macd_slope',
        'kdj_k', 'kdj_d', 'kdj_j', 'fib_382', 'fib_618', 'fib_50'
    ]
    
    return [tuple(x) for x in df.reindex(columns=db_columns).to_numpy()]

def klines_to_dataframe(klines: List[List[str]]) -> pd.DataFrame:
    """
    Convert MEXC klines list to pandas DataFrame.
    Columns: timestamp (index), open, high, low, close, volume.
    """
    if not klines or len(klines) < 2:
        return pd.DataFrame()
    
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'
    ])
    
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    return df[['open', 'high', 'low', 'close', 'volume']]

def ma_crossover_signal(df: pd.DataFrame, short_period: int = 50, long_period: int = 200) -> Tuple[bool, List[str]]:
    """
    MA Crossover: Returns (signal, ['MA_CROSSOVER']) or (False, []).
    """
    if len(df) < long_period + 1:
        logger.debug(f"Insufficient data for MA {short_period}/{long_period}: {len(df)} rows")
        return False, []
    
    close_prices = df['close']
    sma_short = ta.sma(close_prices, length=short_period)
    sma_long = ta.sma(close_prices, length=long_period)

    if pd.isna(sma_long.iloc[-1]) or pd.isna(sma_long.iloc[-2]):
        return False, []

    current_cross = sma_short.iloc[-1] > sma_long.iloc[-1]
    prev_cross = sma_short.iloc[-2] <= sma_long.iloc[-2]
    fresh_crossover = current_cross and prev_cross
    
    # Log golden cross (non-fresh)
    if current_cross and not fresh_crossover:
        symbol = getattr(df, '_symbol', 'UNKNOWN')
        diff_pct = ((sma_short.iloc[-1] - sma_long.iloc[-1]) / sma_long.iloc[-1] * 100)
        logger.debug(f"GOLDEN CROSS (ongoing): {symbol} | Short: {sma_short.iloc[-1]:.4f} | Long: {sma_long.iloc[-1]:.4f} | Diff: {diff_pct:.2f}%")
    
    if symbol := getattr(df, '_symbol', None) == 'BTCUSDT':
        logger.debug(f"BTCUSDT: Short[-1]:{sma_short.iloc[-1]:.2f}, Long[-1]:{sma_long.iloc[-1]:.2f} | Fresh:{fresh_crossover}")

    if fresh_crossover:
        return True, ['MA_CROSSOVER']
    return False, []

def rsi_oversold_signal(df: pd.DataFrame, period: int = 14, oversold_threshold: float = 30.0) -> Tuple[bool, List[str]]:
    """
    RSI Oversold: Supports <20 or <30. Returns (signal, ['RSI_OVERSOLD_{threshold}']).
    """
    if len(df) < period:
        return False, []
    
    rsi = ta.rsi(df['close'], length=period)
    if pd.isna(rsi.iloc[-1]):
        return False, []
    
    signal_name = f'RSI_OVERSOLD_{int(oversold_threshold)}'
    if rsi.iloc[-1] < oversold_threshold:
        return True, [signal_name]
    return False, []

def fib_retracement_signal(df: pd.DataFrame, lookback: int = 20, fib_level: float = 0.618) -> Tuple[bool, List[str]]:
    """
    Fib Bounce: Price > Fib support (e.g., 61.8%) from recent high-low swing, in uptrend (above MA_200).
    Returns (signal, ['FIB_BOUNCE']).
    """
    if len(df) < lookback + 200:  # Need MA_200 + lookback
        return False, []
    
    # Compute MA_200 for uptrend
    ma_200 = ta.sma(df['close'], length=200)
    if pd.isna(ma_200.iloc[-1]) or df['close'].iloc[-1] <= ma_200.iloc[-1]:
        return False, []  # Not in uptrend
    
    recent_data = df.tail(lookback)
    high = recent_data['high'].max()
    low = recent_data['low'].min()
    diff = high - low
    fib_support = high - (diff * fib_level)
    current = df['close'].iloc[-1]
    
    bounce = current > fib_support
    if bounce:
        return True, ['FIB_BOUNCE']
    return False, []

def get_buy_signal(klines: List[List[str]], strategy: str = 'MA_CROSSOVER') -> Dict[str, Any]:
    """
    Enhanced: Returns {'signal': bool, 'active_indicators': ['IND1', 'IND2'], 'strength': float (0-1)}.
    Strategies: 'MA_CROSSOVER', 'RSI_20', 'MA_RSI_COMBO' (MA + RSI<30), 'MA_FIB_COMBO' (MA + Fib).
    Set df._symbol = symbol in caller for logs.
    """
    df = klines_to_dataframe(klines)
    if df.empty:
        return {'signal': False, 'active_indicators': [], 'strength': 0.0}
    
    df._symbol = 'UNKNOWN'  # Override in main.py: df._symbol = symbol
    
    all_indicators = []
    signal = False
    strength = 0.0
    
    if strategy == 'MA_CROSSOVER':
        ma_sig, ma_inds = ma_crossover_signal(df)
        all_indicators.extend(ma_inds)
        signal = ma_sig
        strength = 1.0 if signal else 0.0
    elif strategy == 'RSI_20':
        rsi_sig, rsi_inds = rsi_oversold_signal(df, oversold_threshold=20.0)
        all_indicators.extend(rsi_inds)
        signal = rsi_sig
        strength = 0.8 if signal else 0.0  # High conviction for extreme oversold
    elif strategy == 'MA_RSI_COMBO':
        ma_sig, ma_inds = ma_crossover_signal(df)
        rsi_sig, rsi_inds = rsi_oversold_signal(df, oversold_threshold=30.0)
        all_indicators.extend(ma_inds + rsi_inds)
        signal = ma_sig and rsi_sig
        strength = 1.2 if signal else 0.0  # Bonus for combo
    elif strategy == 'MA_FIB_COMBO':
        ma_sig, ma_inds = ma_crossover_signal(df)
        fib_sig, fib_inds = fib_retracement_signal(df)
        all_indicators.extend(ma_inds + fib_inds)
        signal = ma_sig or fib_sig  # OR for Fib as alt entry
        strength = 1.0 if signal else 0.0
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    if signal and len(all_indicators) > 1:
        logger.info(f"COMBO SIGNAL: {', '.join(all_indicators)} activated for {df._symbol}")
    
    return {'signal': signal, 'active_indicators': all_indicators, 'strength': min(strength, 1.0)}

def get_signal_metrics(klines: List[List[str]]) -> Optional[Dict[str, float]]:
    """
    Enhanced metrics: Add Fib support, bounce dist.
    """
    df = klines_to_dataframe(klines)
    if df.empty or len(df) < 200:
        return None
    
    rsi = ta.rsi(df['close'], length=14).iloc[-1]
    sma_50 = ta.sma(df['close'], length=50).iloc[-1]
    sma_200 = ta.sma(df['close'], length=200).iloc[-1]
    
    if pd.isna(rsi) or pd.isna(sma_50) or pd.isna(sma_200):
        return None

    # Fib metric
    lookback=20
    if len(df) >= lookback:
        recent = df.tail(lookback)
        high, low = recent['high'].max(), recent['low'].min()
        diff = high - low
        fib_618 = high - (diff * 0.618)
        bounce_dist = ((df['close'].iloc[-1] - fib_618) / fib_618 * 100) if fib_618 > 0 else 0

    return {
        'rsi': rsi,
        'ma_diff_pct': ((sma_50 - sma_200) / sma_200 * 100) if sma_200 != 0 else 0,
        'volume_ma': df['volume'].tail(20).mean(),
        'fib_bounce_pct': bounce_dist
    }