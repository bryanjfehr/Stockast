import logging
import pandas as pd
import numpy as np
from typing import Optional

# Hypothetical imports from your existing utils
# from . import indicators

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_ema(series: pd.Series, span: int = 10) -> pd.Series:
    """Calculates the Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()

def convert_to_rgb(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Converts OHLCV DataFrame to an RGB + Line format using relativistic normalization.

    - R (Red): Relativistic Volume Percentage Change.
    - G (Green): Sentiment Score (placeholder).
    - B (Blue): Relativistic Volatility.
    - Line (embed_4): Exponential Moving Average of the close price.

    Args:
        df: A Pandas DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.

    Returns:
        A new DataFrame with 'R', 'G', 'B', 'embed_4' columns, or None if input is invalid.
    """
    if not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
        logging.error("Input DataFrame is missing required OHLCV columns.")
        return None

    if len(df) < 21: # Need enough data for rolling calculations
        logging.warning("DataFrame has insufficient data for RGB conversion, skipping.")
        return None

    proc_df = df.copy()

    try:
        # --- Relativistic Features ---
        # 1. Price Change %
        proc_df['change_pct'] = proc_df['close'].pct_change() * 100

        # 2. Volume Change %
        proc_df['volume_pct'] = proc_df['volume'].pct_change() * 100

        # 3. Volatility (High-Low range as a percentage of the low)
        proc_df['volatility_pct'] = (proc_df['high'] - proc_df['low']) / proc_df['low'] * 100

        # 4. Sentiment (Placeholder - replace with actual data source, e.g., LunarCrush)
        proc_df['sentiment_pct'] = np.random.uniform(30, 80, len(proc_df))

        # --- Normalization References ---
        # Use rolling means to create a dynamic baseline for normalization
        vol_sma = proc_df['volume'].rolling(20).mean()
        volatility_sma = proc_df['volatility_pct'].rolling(20).mean()

        # --- Channel Calculations (Relativistic Normalization) ---
        # R: Volume strength relative to its recent simple moving average
        # The divisor avoids division by zero and normalizes the percentage change
        r_divisor = (vol_sma / proc_df['volume'].mean())
        r_divisor.replace(0, 1, inplace=True) # Avoid division by zero
        proc_df['R'] = np.clip((proc_df['volume_pct'] / r_divisor) * 2.55, 0, 255)

        # G: Sentiment score, scaled from 0-100 to 0-255
        proc_df['G'] = np.clip(proc_df['sentiment_pct'] * 2.55, 0, 255)

        # B: Volatility relative to its recent simple moving average
        b_divisor = (volatility_sma / proc_df['volatility_pct'].mean())
        b_divisor.replace(0, 1, inplace=True) # Avoid division by zero
        proc_df['B'] = np.clip((proc_df['volatility_pct'] / b_divisor) * 2.55, 0, 255)

        # Line: Price EMA for trend context
        proc_df['embed_4'] = calculate_ema(proc_df['close'], span=10)

        # Drop rows with NaN values resulting from rolling calculations
        proc_df.dropna(inplace=True)

        # --- Final Normalization to 0-1 range for the model ---
        # Normalize RGB channels
        proc_df[['R', 'G', 'B']] = proc_df[['R', 'G', 'B']] / 255.0

        # Normalize the EMA line value relative to its own min/max in the series
        min_embed = proc_df['embed_4'].min()
        max_embed = proc_df['embed_4'].max()
        if (max_embed - min_embed) > 1e-8:
            proc_df['embed_4'] = (proc_df['embed_4'] - min_embed) / (max_embed - min_embed)
        else:
            proc_df['embed_4'] = 0.5 # Assign a neutral value if data is flat

        return proc_df[['R', 'G', 'B', 'embed_4']]

    except Exception as e:
        logging.error(f"An error occurred during RGB conversion: {e}", exc_info=True)
        return None