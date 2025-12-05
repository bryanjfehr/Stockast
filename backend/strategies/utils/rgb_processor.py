import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Tuple

def _normalize_relativistic(series: pd.Series) -> pd.Series:
    """Normalizes a series to a 0-255 scale based on its percentile rank."""
    return (series.rank(pct=True) * 255).astype(int)

def to_rgb_chart(df: pd.DataFrame, ema_period: int = 20) -> Tuple[pd.DataFrame, List[str]]:
    """
    Converts OHLCV and sentiment data into an RGB chart representation.

    Args:
        df: DataFrame with 'volume', 'close', and sentiment columns (e.g., 'sentiment_pct').
        ema_period: The period for the price EMA calculation.

    Returns:
        A tuple containing:
        - The DataFrame with added R, G, B, line_val, and hex_color columns.
        - A list of hex color strings for plotting.
    """
    if df.empty:
        return pd.DataFrame(), []

    df_rgb = df.copy()

    # --- RGB Channels ---
    # R: Volume
    df_rgb['volume_pct'] = df_rgb['volume'].rank(pct=True)
    df_rgb['R'] = (df_rgb['volume_pct'] * 255).astype(int)

    # G: Sentiment (assuming a 'sentiment_pct' column exists or is calculated)
    if 'sentiment_pct' not in df_rgb.columns:
        # Placeholder if sentiment is not pre-calculated
        df_rgb['sentiment_pct'] = np.random.rand(len(df_rgb))
    df_rgb['G'] = (df_rgb['sentiment_pct'] * 255).astype(int)

    # B: Volatility (e.g., ATR)
    # Placeholder for volatility calculation
    high_low = df_rgb['high'] - df_rgb['low']
    high_close = np.abs(df_rgb['high'] - df_rgb['close'].shift())
    low_close = np.abs(df_rgb['low'] - df_rgb['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()
    df_rgb['volatility_pct'] = atr.rank(pct=True)
    df_rgb['B'] = (df_rgb['volatility_pct'].fillna(0) * 255).astype(int)


    # --- Line Value (4th channel) ---
    # Price EMA, normalized from 0 to 1
    df_rgb['price_ema'] = df_rgb['close'].ewm(span=ema_period, adjust=False).mean()
    min_ema = df_rgb['price_ema'].min()
    max_ema = df_rgb['price_ema'].max()
    df_rgb['line_val'] = (df_rgb['price_ema'] - min_ema) / (max_ema - min_ema) if max_ema > min_ema else 0.5

    # --- Hex Colors ---
    hex_colors = [f'#{r:02x}{g:02x}{b:02x}' for r, g, b in zip(df_rgb['R'], df_rgb['G'], df_rgb['B'])]
    df_rgb['hex_color'] = hex_colors

    return df_rgb, hex_colors

def plot_rgb_candles(df: pd.DataFrame, title: str = "RGB Candle Chart"):
    """
    Visualizes the RGB chart using Matplotlib.

    Args:
        df: DataFrame processed by to_rgb_chart.
        title: The title for the plot.
    """
    if df.empty or 'hex_color' not in df.columns:
        print("DataFrame is empty or missing 'hex_color' column. Cannot plot.")
        return

    fig, ax = plt.subplots(figsize=(15, 7))
    
    # Plotting candles
    for i, row in df.iterrows():
        color = row['hex_color']
        ax.plot([i, i], [row['low'], row['high']], color='gray', linewidth=1)  # Wick
        candle_height = abs(row['close'] - row['open'])
        candle_bottom = min(row['open'], row['close'])
        rect = mpatches.Rectangle((i - 0.4, candle_bottom), 0.8, candle_height, facecolor=color, edgecolor='black')
        ax.add_patch(rect)

    # Plotting EMA line
    ax.plot(df.index, df['price_ema'], color='white', linestyle='-', linewidth=2, label='Price EMA')

    ax.set_title(title)
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.6)
    plt.show()

def process_multiple_assets(asset_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Processes a dictionary of DataFrames for multiple assets.
    """
    processed_dfs = {}
    for symbol, df in asset_dfs.items():
        processed_df, _ = to_rgb_chart(df)
        processed_dfs[symbol] = processed_df
    return processed_dfs

if __name__ == '__main__':
    # Example Usage
    # 1. Create a sample DataFrame
    data = {
        'timestamp': pd.to_datetime(pd.date_range('2023-01-01', periods=100)),
        'open': np.random.uniform(95, 105, 100),
        'high': np.random.uniform(100, 110, 100),
        'low': np.random.uniform(90, 100, 100),
        'close': np.random.uniform(98, 108, 100),
        'volume': np.random.uniform(1000, 5000, 100),
        'sentiment_pct': np.random.rand(100)
    }
    sample_df = pd.DataFrame(data).set_index('timestamp')
    
    # 2. Process the DataFrame
    rgb_df, _ = to_rgb_chart(sample_df)
    
    # 3. Plot the result
    plot_rgb_candles(rgb_df, title="Sample RGB Chart")

    # 4. Example with multiple assets
    asset_data = {
        "BTC/USDT": sample_df,
        "ETH/USDT": sample_df.apply(lambda x: x * np.random.uniform(0.5, 1.5)) # Create some variation
    }
    processed_assets = process_multiple_assets(asset_data)
    print("\nProcessed ETH/USDT data:")
    print(processed_assets["ETH/USDT"].head())
    plot_rgb_candles(processed_assets["ETH/USDT"], title="ETH/USDT RGB Chart")