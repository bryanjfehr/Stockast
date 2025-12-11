# strategies.py
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from indicators import (calculate_sma, calculate_rsi, calculate_macd, volume_spike, volume_ratio, 
                       calculate_volatility, hourly_trend, calculate_probability_score_series, momentum_roc)
from db import get_strategy_config  # New func: Fetch by name
from config import DB_COLS_1H, DB_COLS_15M, DB_COLS_5M, MOMENTUM_PERIODS

logger = logging.getLogger(__name__)

def calculate_and_enrich_klines(symbol: str, klines: List[List[str]], interval: str) -> tuple[List[tuple], List[str]]:
    """Calculates indicators based on interval and returns enriched data and column list."""
    if not klines:
        return []
    
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'])
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # --- Calculate all possible indicators ---
    # This is slightly inefficient but simplifies logic. We calculate everything
    # and then select the columns needed for the specific interval.
    df['ma_10'] = calculate_sma(df['close'], 10)
    df['ma_50'] = calculate_sma(df['close'], 50)
    df['rsi_14'] = calculate_rsi(df['close'], 14)
    macd = calculate_macd(df['close'])
    df['macd'] = macd['macd']
    df['macd_signal'] = macd['signal']
    df['macd_hist'] = macd['hist']
    df['volume_spike'] = volume_spike(df)
    df['vol_ratio_5'] = volume_ratio(df, 5)
    df['vol_ratio_10'] = volume_ratio(df, 10)
    df['volatility_5m'] = calculate_volatility(df, interval='5m')
    df['volatility_1h'] = calculate_volatility(df, interval='1h')
    df['hourly_trend'] = hourly_trend(df)
    df['prob_score'] = calculate_probability_score_series(df)
    df['momentum_roc'] = momentum_roc(df['close'], periods=MOMENTUM_PERIODS)
    
    df['symbol'] = symbol
    df.replace({np.nan: None}, inplace=True)
    
    # --- Select columns based on interval ---
    if interval == '1h':
        db_columns = DB_COLS_1H
    elif interval == '15m':
        db_columns = DB_COLS_15M
    elif interval == '5m':
        db_columns = DB_COLS_5M
    else:
        raise ValueError(f"Unknown interval for enrichment: {interval}")

    enriched_tuples = [tuple(row) for row in df.reindex(columns=db_columns).to_numpy()]
    return enriched_tuples, db_columns

def evaluate_strategy(df: pd.DataFrame, strategy_name: str = 'BALANCED') -> Dict[str, Any]:
    """Fetch config, count matching signals, check prob."""
    config = get_strategy_config(strategy_name)  # Implement in db.py: SELECT * WHERE name=?
    if not config:
        raise ValueError(f"Strategy '{strategy_name}' not found.")
    
    if len(df) < 50: # Not enough data for reliable indicators
        return {'signal': False, 'active_indicators': [], 'prob_score': 0.0, 'confidence': 0.0, 'signal_count': 0}

    thresholds = json.loads(config['thresholds'])
    min_signals = config['min_signals']
    prob_threshold = config['prob_threshold']
    
    # Compute indicators (latest values)
    latest = df.iloc[-1]

    # Helper to check for valid numeric values (not None, not NaN)
    def is_valid(value):
        return isinstance(value, (int, float)) and not np.isnan(value)

    indicators = {
        'rsi_oversold': is_valid(latest['rsi_14']) and latest['rsi_14'] < thresholds.get('rsi_oversold', 30),
        'vol_spike': is_valid(latest['volume_spike']) and latest['volume_spike'] == 1 and thresholds.get('vol_spike', True),
        'vol_ratio_high': is_valid(latest['vol_ratio_5']) and latest['vol_ratio_5'] > thresholds.get('vol_mult', 1.5),
        'trend_bull': is_valid(latest['hourly_trend']) and latest['hourly_trend'] > 0,
        'ma_cross': is_valid(latest['ma_10']) and is_valid(latest['ma_50']) and latest['ma_10'] > latest['ma_50'],
        'macd_bull': is_valid(latest['macd_hist']) and latest['macd_hist'] > 0,
        'high_vol': is_valid(latest['volatility_1h']) and latest['volatility_1h'] > 0.02,
        'prob_up': is_valid(latest['prob_score']) and latest['prob_score'] > 0
    }
    
    active_signals = [k for k, v in indicators.items() if v]
    signal_count = len(active_signals)
    prob_score = latest['prob_score'] if is_valid(latest['prob_score']) else 0.0
    
    confidence = min(signal_count / len(indicators), 1.0) * (prob_score if prob_score > 0 else 0)
    
    signal = (signal_count >= min_signals) and (prob_score >= prob_threshold)
    
    if signal:
        logger.info(f"STRATEGY '{strategy_name}': {signal_count}/{len(indicators)} signals | Prob: {prob_score:.2f} | Confidence: {confidence:.2f} | Active: {', '.join(active_signals)}")
    
    return {
        'signal': signal,
        'active_indicators': active_signals,
        'prob_score': prob_score,
        'confidence': confidence,
        'signal_count': signal_count
    }

# get_buy_signal alias for backward compat
def get_buy_signal(klines: List[List[str]], strategy_name: str = 'BALANCED') -> Dict[str, Any]:
    # Enrich raw klines to create the DataFrame needed by evaluate_strategy.
    # This is necessary for the backtester to function correctly. Assumes 1h for backtesting.
    enriched_tuples = calculate_and_enrich_klines("BACKTEST", klines)
    if not enriched_tuples:
        return {'signal': False, 'active_indicators': [], 'prob_score': 0.0, 'confidence': 0.0, 'signal_count': 0}
    
    df = pd.DataFrame(enriched_tuples, columns=DB_COLS)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)

    return evaluate_strategy(df, strategy_name)

def klines_to_dataframe(klines: List[List[str]]) -> pd.DataFrame:
    """Convert raw klines to DataFrame with numeric types."""
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'])
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def get_strategy_metrics(df: pd.DataFrame) -> Optional[Dict[str, float]]:
    """Extract latest metrics from enriched DF."""
    if df.empty or len(df) < 50:
        return None
    latest = df.iloc[-1]
    return {
        'prob_score': latest['prob_score'],
        'confidence': latest.get('confidence', 0),  # If computed in eval
        'hourly_trend': latest['hourly_trend'],
        'rsi': latest['rsi_14'],  # For backward compat
        'ma_diff_pct': ((latest['ma_10'] - latest['ma_50']) / latest['ma_50'] * 100) if latest['ma_50'] else 0
    }