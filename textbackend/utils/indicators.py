import logging
import talib
import pandas as pd

logging.basicConfig(level=logging.INFO)

def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Computes MACD for a given DataFrame.
    """
    return talib.MACD(df['close'], fastperiod=fast, slowperiod=slow, signalperiod=signal)

def compute_rsi(df: pd.DataFrame, period: int = 14):
    """
    Computes RSI for a given DataFrame.
    """
    return talib.RSI(df['close'], timeperiod=period)

def compute_kdj(df: pd.DataFrame, fastk_period: int = 9, slowk_period: int = 3, slowd_period: int = 3):
    """
    Computes KDJ for a given DataFrame.
    """
    low_min = df['low'].rolling(window=fastk_period).min()
    high_max = df['high'].rolling(window=fastk_period).max()
    k_value = 100 * (df['close'] - low_min) / (high_max - low_min)
    d_value = k_value.rolling(window=slowk_period).mean()
    j_value = 3 * d_value - 2 * k_value
    return k_value, d_value, j_value

def compute_volume_sma(df: pd.DataFrame, period: int = 20):
    """
    Computes the Simple Moving Average of volume for a given DataFrame.
    """
    return talib.SMA(df['volume'], timeperiod=period)