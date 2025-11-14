import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_synthetic_breakout_data(n_periods=100):
    """Generate synthetic OHLCV data for a bullish breakout with parabolic top."""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=n_periods, freq='1H')
    close = np.cumsum(np.random.normal(0.5, 2, n_periods)) + 100  # Uptrend with noise
    # Simulate breakout surge (periods 40-60), then exhaustion
    close[40:50] += np.linspace(0, 20, 10)  # Initial breakout
    close[50:70] += np.cumsum(np.random.normal(1, 1, 20))  # Parabolic climb
    close[70:] -= np.linspace(0, 15, n_periods-70)  # Reversal
    high = close + np.random.uniform(0, 3, n_periods)
    low = close - np.random.uniform(0, 3, n_periods)
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    # Volume: Spike on breakout, climax at top, then drop
    volume = np.full(n_periods, 1000)
    volume[40:50] *= 3  # Breakout spike
    volume[60:70] *= 5  # Top climax
    volume[70:] *= 0.5  # Decline
    df = pd.DataFrame({'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Volume': volume}, index=dates)
    return df

def compute_rsi(close, period=14):
    """Compute RSI manually."""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(close, fast=12, slow=26, signal=9):
    """Compute MACD manually."""
    ema_fast = close.ewm(span=fast).mean()
    ema_slow = close.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def parabolic_sar(high, low, af_step=0.02, af_max=0.2):
    """Parabolic SAR implementation (from standard formula)."""
    length = len(high)
    sar = np.zeros(length)
    ep = np.zeros(length)
    af = np.full(length, af_step)
    uptrend = [True] * length
    
    # Initialize
    sar[0] = low[0]
    ep[0] = high[0]
    
    for i in range(1, length):
        sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])
        
        if uptrend[i-1]:
            sar[i] = min(sar[i], low[i-1], low[i-2] if i > 1 else low[i-1])
            if high[i] > ep[i-1]:
                ep[i] = high[i]
                af[i] = min(af[i-1] + af_step, af_max)
            else:
                ep[i] = ep[i-1]
                af[i] = af[i-1]
            if sar[i] > low[i]:
                uptrend[i] = False
                sar[i] = ep[i-1]
                ep[i] = low[i]
                af[i] = af_step
            else:
                uptrend[i] = True
        else:
            # Similar logic for downtrend (symmetric)
            sar[i] = max(sar[i], high[i-1], high[i-2] if i > 1 else high[i-1])
            if low[i] < ep[i-1]:
                ep[i] = low[i]
                af[i] = min(af[i-1] + af_step, af_max)
            else:
                ep[i] = ep[i-1]
                af[i] = af[i-1]
            if sar[i] < high[i]:
                uptrend[i] = True
                sar[i] = ep[i-1]
                ep[i] = high[i]
                af[i] = af_step
            else:
                uptrend[i] = False
    
    return sar

def detect_breakout_top(df, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9, vol_period=20, rsi_ob=70, vol_spike_mult=2.0):
    """Detect breakout and map potential top."""
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # Indicators
    df['RSI'] = compute_rsi(close, rsi_period)
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(close, macd_fast, macd_slow, macd_signal)
    df['SAR'] = parabolic_sar(high, low)
    df['Vol_SMA'] = volume.rolling(vol_period).mean()
    df['Breakout_High'] = high.rolling(20).max().shift(1)  # Recent high for breakout detection
    
    # Signals
    df['In_Breakout'] = close > df['Breakout_High']
    df['Vol_Spike'] = volume > df['Vol_SMA'] * vol_spike_mult
    df['Vol_Decline'] = volume < df['Vol_SMA'] * 0.8  # Post-spike decline
    df['RSI_Overbought'] = df['RSI'] > rsi_ob
    df['MACD_Divergence'] = (df['MACD_Hist'] < df['MACD_Hist'].shift(1)) & (close > close.shift(1))  # Bearish divergence
    df['SAR_Flip'] = (df['SAR'].shift(1) < close.shift(1)) & (df['SAR'] > close)  # Flip to resistance
    
    # Top signal: In breakout + momentum exhaustion + volume drop
    df['Top_Signal'] = df['In_Breakout'] & (
        (df['SAR_Flip'] | df['MACD_Divergence']) & 
        df['RSI_Overbought'] & 
        df['Vol_Decline']
    )
    
    projected_top = df.loc[df['Top_Signal'], 'Close'].mean() if df['Top_Signal'].any() else np.nan  # Avg close at signals as 'mapped top'
    
    return df, projected_top

# Run example
df = generate_synthetic_breakout_data()
df_detected, top_price = detect_breakout_top(df)

print("Detected Top Signals:")
print(df[df['Top_Signal']][['Close', 'RSI', 'MACD_Hist', 'Volume', 'SAR']])

print(f"\nMapped Top Price: ${top_price:.2f}")

# Plot for visualization
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
ax1.plot(df.index, df['Close'], label='Close', color='blue')
ax1.plot(df.index, df['SAR'], label='Parabolic SAR', color='orange', marker='.', linestyle='None')
ax1.scatter(df[df['Top_Signal']].index, df[df['Top_Signal']]['Close'], color='red', marker='v', s=100, label='Top Signal')
ax1.set_title('Price and SAR')
ax1.legend()

ax2.plot(df.index, df['MACD_Hist'], label='MACD Histogram', color='green')
ax2.axhline(0, color='black', linestyle='--')
ax2.scatter(df[df['MACD_Divergence']].index, df[df['MACD_Divergence']]['MACD_Hist'], color='purple', marker='o', label='Divergence')
ax2.set_title('MACD Histogram & Divergence')
ax2.legend()

ax3.bar(df.index, df['Volume'], alpha=0.3, label='Volume')
ax3.plot(df.index, df['Vol_SMA'], color='red', label='Vol SMA')
ax3.scatter(df[df['Vol_Spike']].index, df[df['Vol_Spike']]['Volume'], color='green', marker='^', label='Spike')
ax3.scatter(df[df['Vol_Decline']].index, df[df['Vol_Decline']]['Volume'], color='brown', marker='x', label='Decline')
ax3.set_title('Volume Analysis')
ax3.legend()

plt.tight_layout()
plt.show()