import pandas as pd
import numpy as np
import ccxt  # For live data; fallback to synthetic
import time

def fetch_btc_data(exchange=None, days_back=365 + 1):  # Yearly + buffer
    """Fetch BTC OHLCV (4h timeframe for medium-term)."""
    if exchange:
        since = int((time.time() - days_back * 86400) * 1000)
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='4h', since=since, limit=1000)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    else:
        # Synthetic for demo (real: replace with fetch)
        np.random.seed(42)
        n = 2190  # ~3 years 4h bars
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=n, freq='4H'),
            'open': 100 + np.cumsum(np.random.normal(0, 0.5, n)),
            'high': 100 + np.cumsum(np.random.normal(0, 0.5, n)) + np.random.uniform(0, 1, n),
            'low': 100 + np.cumsum(np.random.normal(0, 0.5, n)) - np.random.uniform(0, 1, n),
            'close': 100 + np.cumsum(np.random.normal(0, 0.5, n)),
            'volume': np.random.uniform(1000, 5000, n)
        })
        # Simulate yearly cycle: Big uptrend 2024-2025
        df.loc['2024':'2025', 'close'] *= 1.5
    return df

def compute_ranges(df):
    """Compute yearly and 24h ranges."""
    df['date'] = df['timestamp'].dt.date
    yearly = df.groupby('date.dt.year').agg({'high': 'max', 'low': 'min', 'close': 'last'}).reset_index()
    current_year = df['timestamp'].dt.year.max()
    yearly_high = yearly.loc[yearly['date.dt.year'] == current_year, 'high'].iloc[0]
    yearly_low = yearly.loc[yearly['date.dt.year'] == current_year, 'low'].iloc[0]
    current_price = df['close'].iloc[-1]
    pos_in_range = (current_price - yearly_low) / (yearly_high - yearly_low) * 100 if yearly_high > yearly_low else 50
    
    # 24h range: Last 6 bars (4h * 6 = 24h)
    recent = df.tail(6)
    h24_high, h24_low = recent['high'].max(), recent['low'].min()
    h24_range_pct = (h24_high - h24_low) / h24_low * 100
    avg_h24_vol = df['high'].rolling(150).apply(lambda x: (x.max() - x.min()) / x.min() * 100).mean()  # ~25 days avg
    
    return pos_in_range, h24_range_pct, avg_h24_vol, current_price

def medium_btc_strategy(df, pos_in_range, h24_range_pct, avg_h24_vol):
    """Generate medium-term signals with range filters."""
    close, high, low, volume = df['close'], df['high'], df['low'], df['volume']
    
    # Indicators (from prior code)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    hist = macd - signal
    
    vol_sma = volume.rolling(20).mean()
    
    # Signals with range filters
    bullish_bias = pos_in_range > 50
    vol_confirm = h24_range_pct > avg_h24_vol * 0.8  # Above avg for entry
    macd_bull = (macd > signal) & (macd.shift(1) <= signal.shift(1))  # Crossover up
    rsi_neutral = 40 < rsi < 60  # Avoid extremes
    vol_spike = volume > vol_sma * 1.5
    
    df['Buy_Signal'] = macd_bull & rsi_neutral & vol_spike & bullish_bias & vol_confirm
    df['Sell_Signal'] = (macd < signal) & (rsi > 60) & (volume < vol_sma)  # Opposite for exit
    
    # Simulate trade: Hold 1-2 days (6-12 bars), TP/SL 3% scaled by h24 vol
    tp_pct = min(0.03 + (h24_range_pct / 100) * 0.02, 0.05)  # 3-5%
    sl_pct = -tp_pct
    
    signals = df[df['Buy_Signal'] | df['Sell_Signal']]
    return df, signals, tp_pct

# Example Run (Integrate with MEXC via CCXT)
exchange = ccxt.mexc()  # Add keys in prod
df = fetch_btc_data(exchange)
pos_in_range, h24_range_pct, avg_h24_vol, current_price = compute_ranges(df)
df, signals, tp_pct = medium_btc_strategy(df, pos_in_range, h24_range_pct, avg_h24_vol)

print(f"Current BTC: ${current_price:.2f} | Pos in Yearly Range: {pos_in_range:.1f}%")
print(f"24h Range: {h24_range_pct:.2f}% (Avg: {avg_h24_vol:.2f}%) | TP/SL: ±{tp_pct*100:.1f}%")
print("Recent Signals:\n", signals[['timestamp', 'close', 'Buy_Signal', 'Sell_Signal']].tail())

# Backtest Snippet (Add to your base.py)
def backtest_medium(df, initial_capital=10000):
    capital = initial_capital
    position = 0
    for i in range(1, len(df)):
        if df['Buy_Signal'].iloc[i] and position == 0:
            position = capital * 0.02 / df['close'].iloc[i]  # 2% risk
            entry = df['close'].iloc[i]
        elif position > 0:
            pnl = (df['close'].iloc[i] - entry) / entry
            if df['Sell_Signal'].iloc[i] or pnl >= tp_pct or pnl <= sl_pct:
                capital += capital * pnl * 0.02  # Scaled return
                position = 0
    return (capital - initial_capital) / initial_capital * 100  # ROI %

roi = backtest_medium(df)
print(f"Backtested ROI: {roi:.1f}%")