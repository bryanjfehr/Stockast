import logging
from typing import List, Dict, Any

import pandas as pd
import talib
from sqlalchemy.orm import Session

# Assuming these paths and models exist based on the project structure.
# The dependency context was empty, so we rely on the pseudo-code's description.
from app.crud import crud_stock
from app.models.stock_data import StockData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for signal generation
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70


def calculate_technical_indicators(historical_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators like RSI and MACD on historical stock data.

    Args:
        historical_data: DataFrame with 'close', 'high', 'low', 'volume' columns.

    Returns:
        DataFrame with added technical indicator columns.
    """
    if 'close' not in historical_data.columns:
        raise ValueError("Input DataFrame must contain a 'close' column.")

    data_with_indicators = historical_data.copy()

    # Calculate Relative Strength Index (RSI)
    data_with_indicators['rsi'] = talib.RSI(data_with_indicators['close'])

    # Calculate Moving Average Convergence Divergence (MACD)
    macd, macd_signal, macd_hist = talib.MACD(data_with_indicators['close'])
    data_with_indicators['macd'] = macd
    data_with_indicators['macd_signal'] = macd_signal
    data_with_indicators['macd_hist'] = macd_hist

    # Drop rows with NaN values that result from indicator calculation warm-up period
    data_with_indicators.dropna(inplace=True)

    return data_with_indicators


def generate_signals(data_with_indicators: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes technical indicators to generate 'BULLISH' or 'BEARISH' signals.

    Args:
        data_with_indicators: DataFrame containing technical indicator columns.

    Returns:
        A dictionary containing the signal type and the reason.
    """
    required_cols = ['rsi', 'macd', 'macd_signal']
    if not all(col in data_with_indicators.columns for col in required_cols):
        return {'signal_type': 'NEUTRAL', 'reason': 'Missing required indicator columns.'}

    if len(data_with_indicators) < 2:
        return {'signal_type': 'NEUTRAL', 'reason': 'Not enough data to generate a signal.'}

    # Get the last two rows for crossover analysis
    latest = data_with_indicators.iloc[-1]
    previous = data_with_indicators.iloc[-2]

    # --- Define Signal Logic Conditions ---
    rsi_oversold = latest['rsi'] < RSI_OVERSOLD
    rsi_overbought = latest['rsi'] > RSI_OVERBOUGHT

    bullish_macd_crossover = latest['macd'] > latest['macd_signal'] and previous['macd'] <= previous['macd_signal']
    bearish_macd_crossover = latest['macd'] < latest['macd_signal'] and previous['macd'] >= previous['macd_signal']

    # --- Combine Conditions to Determine Final Signal ---
    # Check for bearish signals first
    if bearish_macd_crossover and rsi_overbought:
        return {'signal_type': 'STRONG_BEARISH', 'reason': 'MACD bearish crossover and RSI overbought'}
    elif bearish_macd_crossover:
        return {'signal_type': 'BEARISH', 'reason': 'MACD bearish crossover'}
    elif rsi_overbought:
        return {'signal_type': 'BEARISH', 'reason': 'RSI overbought'}

    # Then check for bullish signals
    elif bullish_macd_crossover and rsi_oversold:
        return {'signal_type': 'STRONG_BULLISH', 'reason': 'MACD bullish crossover and RSI oversold'}
    elif bullish_macd_crossover:
        return {'signal_type': 'BULLISH', 'reason': 'MACD bullish crossover'}
    elif rsi_oversold:
        return {'signal_type': 'BULLISH', 'reason': 'RSI oversold'}

    # If no specific signals are triggered, return neutral
    return {'signal_type': 'NEUTRAL', 'reason': 'No clear signal'}


def process_stock_for_signals(db: Session, symbol: str) -> Dict[str, Any]:
    """
    Orchestrates fetching data, calculating indicators, and generating signals for a stock.

    Args:
        db: The database session.
        symbol: The stock symbol to process.

    Returns:
        A dictionary containing the signal, reason, and symbol.
    """
    logger.info(f"Starting signal processing for symbol: {symbol}")

    historical_data_models: List[StockData] = crud_stock.get_historical_data(db, symbol)

    if not historical_data_models:
        logger.warning(f"No historical data found for symbol: {symbol}")
        return {'symbol': symbol, 'signal_type': 'NEUTRAL', 'reason': 'No historical data available'}

    # Convert list of SQLAlchemy models to a Pandas DataFrame
    # Assuming the StockData model has these attributes.
    data_list = [
        {
            "date": record.date,
            "open": record.open,
            "high": record.high,
            "low": record.low,
            "close": record.close,
            "volume": record.volume
        }
        for record in historical_data_models
    ]
    df = pd.DataFrame(data_list)

    # Ensure data types are correct and set a chronological index
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)

    # Ensure numeric types for calculation
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col])

    # Calculate technical indicators
    try:
        df_with_indicators = calculate_technical_indicators(df)
    except ValueError as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        return {'symbol': symbol, 'signal_type': 'NEUTRAL', 'reason': f'Indicator calculation error: {e}'}

    # Generate signals from the indicators
    signal = generate_signals(df_with_indicators)

    # Add symbol to the final result
    signal['symbol'] = symbol

    logger.info(f"Signal for {symbol}: {signal['signal_type']} - {signal['reason']}")

    return signal
