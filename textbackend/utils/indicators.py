import numpy as np
import talib

def calculate_macd(close_prices: np.ndarray, fastperiod=12, slowperiod=26, signalperiod=9):
    """Calculates MACD."""
    return talib.MACD(close_prices, fastperiod, slowperiod, signalperiod)

def calculate_rsi(close_prices: np.ndarray, timeperiod=14):
    """Calculates RSI."""
    return talib.RSI(close_prices, timeperiod)

def calculate_kdj(high_prices: np.ndarray, low_prices: np.ndarray, close_prices: np.ndarray, fastk_period=9, slowk_period=3, slowd_period=3):
    """Calculates KDJ."""
    return talib.STOCH(high_prices, low_prices, close_prices, fastk_period, slowk_period, 0, slowd_period, 0)

def calculate_volume_sma(volume: np.ndarray, timeperiod=20):
    """Calculates simple moving average of volume."""
    return talib.SMA(volume, timeperiod)
