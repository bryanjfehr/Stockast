import pandas as pd
import numpy as np
import talib

def calculate_sma(data, period=20):
    """
    Calculate Simple Moving Average (SMA).
    
    :param data: DataFrame with 'Close' column
    :param period: int, number of days for SMA
    :return: Series with SMA values
    """
    return talib.SMA(data['Close'], timeperiod=period)

def calculate_ema(data, period=20):
    """
    Calculate Exponential Moving Average (EMA).
    
    :param data: DataFrame with 'Close' column
    :param period: int, number of days for EMA
    :return: Series with EMA values
    """
    return talib.EMA(data['Close'], timeperiod=period)

def calculate_rsi(data, period=14):
    """
    Calculate Relative Strength Index (RSI).
    
    :param data: DataFrame with 'Close' column
    :param period: int, number of days for RSI
    :return: Series with RSI values
    """
    return talib.RSI(data['Close'], timeperiod=period)

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate Moving Average Convergence Divergence (MACD).
    
    :param data: DataFrame with 'Close' column
    :param fast_period: int, fast EMA period
    :param slow_period: int, slow EMA period
    :param signal_period: int, signal line period
    :return: tuple of Series (MACD, signal line)
    """
    macd, signal, _ = talib.MACD(data['Close'], fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
    return macd, signal

def calculate_bollinger_bands(data, period=20, num_std_dev=2):
    """
    Calculate Bollinger Bands.
    
    :param data: DataFrame with 'Close' column
    :param period: int, number of days for moving average
    :param num_std_dev: float, number of standard deviations for bands
    :return: tuple of Series (upper band, middle band, lower band)
    """
    upper, middle, lower = talib.BBANDS(data['Close'], timeperiod=period, nbdevup=num_std_dev, nbdevdn=num_std_dev)
    return upper, middle, lower

def generate_sma_signals(data, sma_period=20):
    """
    Generate trading signals based on SMA crossover.
    
    :param data: DataFrame with 'Close' column
    :param sma_period: int, period for SMA
    :return: Series with signals (1 for buy, -1 for sell, 0 for no signal)
    """
    sma = calculate_sma(data, sma_period)
    signals = pd.Series(0, index=data.index)
    signals[(data['Close'].shift(1) <= sma.shift(1)) & (data['Close'] > sma)] = 1  # Buy signal
    signals[(data['Close'].shift(1) >= sma.shift(1)) & (data['Close'] < sma)] = -1  # Sell signal
    return signals

def generate_rsi_signals(data, rsi_period=14, overbought=70, oversold=30):
    """
    Generate trading signals based on RSI levels.
    
    :param data: DataFrame with 'Close' column
    :param rsi_period: int, period for RSI
    :param overbought: float, RSI level for overbought
    :param oversold: float, RSI level for oversold
    :return: Series with signals (1 for buy, -1 for sell, 0 for no signal)
    """
    rsi = calculate_rsi(data, rsi_period)
    signals = pd.Series(0, index=data.index)
    signals[rsi < oversold] = 1  # Buy signal
    signals[rsi > overbought] = -1  # Sell signal
    return signals

def generate_macd_signals(data, fast_period=12, slow_period=26, signal_period=9):
    """
    Generate trading signals based on MACD crossover.
    
    :param data: DataFrame with 'Close' column
    :param fast_period: int, fast EMA period
    :param slow_period: int, slow EMA period
    :param signal_period: int, signal line period
    :return: Series with signals (1 for buy, -1 for sell, 0 for no signal)
    """
    macd, signal = calculate_macd(data, fast_period, slow_period, signal_period)
    signals = pd.Series(0, index=data.index)
    signals[(macd.shift(1) <= signal.shift(1)) & (macd > signal)] = 1  # Buy signal
    signals[(macd.shift(1) >= signal.shift(1)) & (macd < signal)] = -1  # Sell signal
    return signals

def generate_bollinger_band_signals(data, bb_period=20, num_std_dev=2):
    """
    Generate trading signals based on Bollinger Bands.
    
    :param data: DataFrame with 'Close' column
    :param bb_period: int, period for moving average
    :param num_std_dev: float, number of standard deviations for bands
    :return: Series with signals (1 for buy, -1 for sell, 0 for no signal)
    """
    upper, _, lower = calculate_bollinger_bands(data, bb_period, num_std_dev)
    signals = pd.Series(0, index=data.index)
    signals[data['Close'] < lower] = 1  # Buy signal
    signals[data['Close'] > upper] = -1  # Sell signal
    return signals

def generate_technical_signals(data, timeframe='mid'):
    """
    Generate technical analysis signals for the given timeframe.
    
    :param data: DataFrame with 'Close' column
    :param timeframe: str, 'short', 'mid', or 'long'
    :return: dict with keys 'sma', 'rsi', 'macd', 'bb', each containing a Series of signals
    """
    if timeframe == 'short':
        sma_period = 5
        rsi_period = 7
        macd_fast, macd_slow, macd_signal = 6, 13, 4
        bb_period, bb_std_dev = 10, 1.5
    elif timeframe == 'mid':
        sma_period = 20
        rsi_period = 14
        macd_fast, macd_slow, macd_signal = 12, 26, 9
        bb_period, bb_std_dev = 20, 2
    elif timeframe == 'long':
        sma_period = 50
        rsi_period = 21
        macd_fast, macd_slow, macd_signal = 26, 52, 9
        bb_period, bb_std_dev = 50, 2.5
    else:
        raise ValueError("Invalid timeframe. Choose 'short', 'mid', or 'long'.")
    
    signals = {
        'sma': generate_sma_signals(data, sma_period),
        'rsi': generate_rsi_signals(data, rsi_period),
        'macd': generate_macd_signals(data, macd_fast, macd_slow, macd_signal),
        'bb': generate_bollinger_band_signals(data, bb_period, bb_std_dev)
    }
    return signals
