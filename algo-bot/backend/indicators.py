# indicators.py
import pandas as pd
import numpy as np
from typing import Dict, Any

def momentum_roc(series: pd.Series, periods: int = 10) -> pd.Series:
    """Rate of Change: (close - close_n) / close_n * 100."""
    return ((series - series.shift(periods)) / series.shift(periods)) * 100

def calculate_sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=length).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """RSI manual calc."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    """MACD, signal, hist."""
    ema_fast = series.ewm(span=fast).mean()
    ema_slow = series.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return {'macd': macd_line, 'signal': signal_line, 'hist': histogram}

def volume_spike(df: pd.DataFrame, multiplier: float = 2.0, period: int = 10) -> pd.Series:
    """1 if current volume > avg * mult (spike)."""
    avg_vol = df['volume'].rolling(window=period).mean()
    return (df['volume'] > (avg_vol * multiplier)).astype(int)

def volume_ratio(df: pd.DataFrame, period: int = 5) -> pd.Series:
    """Current volume / period avg (ratio >1 = above avg)."""
    avg_vol = df['volume'].rolling(window=period).mean()
    return df['volume'] / avg_vol

def calculate_volatility(df: pd.DataFrame, window: int = 5, interval: str = '1h') -> pd.Series:
    """Rolling std of returns, annualized (1h: *sqrt(24*365), 5m: *sqrt(288*24*365)/interval_adjust)."""
    returns = df['close'].pct_change()
    vol = returns.rolling(window=window).std()
    periods_per_year = 24 * 365 if interval == '1h' else (24 * 365 * 12)  # 5m ~12x hourly
    return vol * np.sqrt(periods_per_year)

def hourly_trend(df: pd.DataFrame, short_ma: int = 10, long_ma: int = 50) -> pd.Series:
    """Composite trend: -1 bear, 0 neutral, 1 bull. Factors: price>ma, short>long, MACD hist>0, RSI>50."""
    ma_short = calculate_sma(df['close'], short_ma)
    ma_long = calculate_sma(df['close'], long_ma)
    rsi = calculate_rsi(df['close'])
    macd = calculate_macd(df['close'])['hist']
    
    price_above_ma = (df['close'] > ma_long).astype(int) * 0.25  # Weight 0.25
    short_above_long = (ma_short > ma_long).astype(int) * 0.25
    macd_positive = (macd > 0).astype(int) * 0.25
    rsi_bull = (rsi > 50).astype(int) * 0.25
    
    trend = price_above_ma + short_above_long + macd_positive + rsi_bull
    trend_array = np.where(trend > 0.5, 1, np.where(trend < -0.5, -1, 0))
    return pd.Series(trend_array, index=df.index)

def get_probability_score(df: pd.DataFrame) -> float:
    """-1 to 1 prob (up=1). Weighted avg of 8 indicators (trend=0.3, RSI=0.2, MACD=0.15, vol_spike=0.1, etc.)."""
    if len(df) < 50:  # Min data
        return 0.0
    
    weights = {
        'trend': 0.3, 'rsi': 0.2, 'macd': 0.15, 'vol_spike': 0.1,
        'vol_ratio_5': 0.05, 'vol_ratio_10': 0.05, 'vol_1h': 0.05, 'ma_cross': 0.05
    }
    
    scores = {}
    
    # Trend
    trend = hourly_trend(df).iloc[-1]
    scores['trend'] = trend  # Already -1/1
    
    # RSI: Normalize (oversold bullish)
    rsi = calculate_rsi(df['close']).iloc[-1]
    scores['rsi'] = - (rsi - 50) / 50  # Invert: low RSI = high positive prob
    
    # MACD: Hist direction
    macd_hist = calculate_macd(df['close'])['hist'].iloc[-1]
    scores['macd'] = 1 if macd_hist > 0 else -1
    
    # Vol spike (bullish if spike in uptrend)
    spike = volume_spike(df).iloc[-1]
    scores['vol_spike'] = spike * scores['trend']  # Conditional
    
    # Vol ratios: >1 bullish if trend positive
    vol_r5 = volume_ratio(df, 5).iloc[-1]
    scores['vol_ratio_5'] = (vol_r5 - 1) * 2 * scores['trend']  # Normalize to -1/1, conditional
    vol_r10 = volume_ratio(df, 10).iloc[-1]
    scores['vol_ratio_10'] = (vol_r10 - 1) * 2 * scores['trend']
    
    # Vol: High vol neutral, but + if uptrend
    vol_1h = calculate_volatility(df, interval='1h').iloc[-1]
    scores['vol_1h'] = 0.5 * scores['trend'] if vol_1h > 0.02 else -0.5 * scores['trend']  # Threshold 2%
    
    # MA cross (short > long)
    ma_short = calculate_sma(df['close'], 10).iloc[-1]
    ma_long = calculate_sma(df['close'], 50).iloc[-1]
    scores['ma_cross'] = 1 if ma_short > ma_long else -1
    
    # Weighted avg
    weighted_sum = sum(scores[k] * weights[k] for k in weights)
    return np.clip(weighted_sum, -1, 1)  # -100% to 100%

def calculate_probability_score_series(df: pd.DataFrame) -> pd.Series:
    """
    Vectorized calculation of probability score for an entire DataFrame.
    Returns a Series with a score for each row.
    """
    if len(df) < 50:
        return pd.Series(0.0, index=df.index)

    weights = {
        'trend': 0.3, 'rsi': 0.2, 'macd': 0.15, 'vol_spike': 0.1,
        'vol_ratio_5': 0.05, 'vol_ratio_10': 0.05, 'vol_1h': 0.05, 'ma_cross': 0.05
    }
    
    scores_df = pd.DataFrame(index=df.index)
    
    # Calculate all indicators as Series
    scores_df['trend'] = hourly_trend(df)
    scores_df['rsi'] = - (calculate_rsi(df['close']) - 50) / 50
    scores_df['macd'] = np.sign(calculate_macd(df['close'])['hist'])
    scores_df['vol_spike'] = volume_spike(df) * scores_df['trend']
    scores_df['vol_ratio_5'] = (volume_ratio(df, 5) - 1) * 2 * scores_df['trend']
    scores_df['vol_ratio_10'] = (volume_ratio(df, 10) - 1) * 2 * scores_df['trend']
    
    vol_1h = calculate_volatility(df, interval='1h')
    scores_df['vol_1h'] = np.where(vol_1h > 0.02, 0.5 * scores_df['trend'], -0.5 * scores_df['trend'])
    
    ma_short = calculate_sma(df['close'], 10)
    ma_long = calculate_sma(df['close'], 50)
    scores_df['ma_cross'] = np.where(ma_short > ma_long, 1, -1)
    
    # Calculate weighted sum
    weighted_sum = pd.Series(0.0, index=df.index)
    for k, w in weights.items():
        # Fill NaN with 0 to ensure calculation completes
        weighted_sum += scores_df[k].fillna(0) * w
        
    return weighted_sum.clip(-1, 1)