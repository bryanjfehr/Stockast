import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_synthetic_bearish_data(n_periods=100):
    """Generate synthetic OHLCV data for a bearish breakout with parabolic drop."""
    np.random.seed(42)
    dates = pd.date_range('2025-01-01', periods=n_periods, freq='1H')
    close = np.cumsum(np.random.normal(-0.5, 2, n_periods)) + 100  # Downtrend with noise
    # Simulate resistance break (periods 40-60), then parabolic drop
    close[40:50] -= np.linspace(0, 20, 10)  # Initial breakdown
    close[50:70] -= np.cumsum(np.random.normal(1, 1, 20))  # Parabolic drop
    close[70:] += np.linspace(0, 15, n_periods-70)  # Potential rebound (for realism)
    high = close + np.random.uniform(0, 3, n_periods)
    low = close - np.random.uniform(0, 3, n_periods)
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    # Volume: Spike on breakdown, climax at bottom, then drop
    volume = np.full(n_periods, 1000)
    volume[40:50] *= 3  # Breakdown spike
    volume[60:70] *= 5  # Bottom climax
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

def detect_bearish_breakout(df, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9, vol_period=20, rsi_ob=70, rsi_bb=50, vol_spike_mult=2.0):
    """Detect bearish breakout and map potential sell/short signals."""
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # Indicators
    df['RSI'] = compute_rsi(close, rsi_period)
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(close, macd_fast, macd_slow, macd_signal)
    df['SAR'] = parabolic_sar(high, low)
    df['Vol_SMA'] = volume.rolling(vol_period).mean()
    df['Breakout_Low'] = low.rolling(20).min().shift(1)  # Recent low for breakout detection
    
    # Signals
    df['In_Breakout'] = close < df['Breakout_Low']
    df['Vol_Spike'] = volume > df['Vol_SMA'] * vol_spike_mult
    df['Vol_Decline'] = volume < df['Vol_SMA'] * 0.8  # Post-climax decline (optional for confirmation)
    df['RSI_Overbought_to_Bear'] = (df['RSI'].shift(1) > rsi_ob) & (df['RSI'] < rsi_bb)  # Shift from overbought to bearish
    df['MACD_Bearish'] = (df['MACD'].shift(1) > df['MACD_Signal'].shift(1)) & (df['MACD'] < df['MACD_Signal'])  # Crossover down
    df['SAR_Flip'] = (df['SAR'].shift(1) > close.shift(1)) & (df['SAR'] < close)  # Wait, for bearish: flip to above (resistance)
    # Correction for SAR bearish flip: From below (support) to above (resistance) during downtrend
    df['SAR_Flip_Bear'] = (df['SAR'].shift(1) < close.shift(1)) & (df['SAR'] > close)  # Dots now above price
    
    # Sell/Short signal: In breakout + at least 2 confirmations
    confirmations = df['SAR_Flip_Bear'] + df['MACD_Bearish'] + df['RSI_Overbought_to_Bear'] + df['Vol_Spike']
    df['Sell_Signal'] = df['In_Breakout'] & (confirmations >= 2)
    
    projected_bottom = df.loc[df['Sell_Signal'], 'Close'].mean() if df['Sell_Signal'].any() else np.nan  # Avg close at signals as 'mapped bottom'
    
    return df, projected_bottom

# Run example
df = generate_synthetic_bearish_data()
df_detected, bottom_price = detect_bearish_breakout(df)

print("Detected Sell/Short Signals:")
print(df[df['Sell_Signal']][['Close', 'RSI', 'MACD_Hist', 'Volume', 'SAR']])

print(f"\nMapped Bottom Price (for Short Entry): ${bottom_price:.2f}")

# Plot for visualization
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
ax1.plot(df.index, df['Close'], label='Close', color='blue')
ax1.plot(df.index, df['SAR'], label='Parabolic SAR', color='orange', marker='.', linestyle='None')
ax1.scatter(df[df['Sell_Signal']].index, df[df['Sell_Signal']]['Close'], color='red', marker='v', s=100, label='Sell Signal')
ax1.set_title('Price and SAR')
ax1.legend()

ax2.plot(df.index, df['MACD_Hist'], label='MACD Histogram', color='green')
ax2.axhline(0, color='black', linestyle='--')
ax2.scatter(df[df['MACD_Bearish']].index, df[df['MACD_Bearish']]['MACD_Hist'], color='purple', marker='o', label='Bearish Cross')
ax2.set_title('MACD Histogram & Bearish Cross')
ax2.legend()

ax3.bar(df.index, df['Volume'], alpha=0.3, label='Volume')
ax3.plot(df.index, df['Vol_SMA'], color='red', label='Vol SMA')
ax3.scatter(df[df['Vol_Spike']].index, df[df['Vol_Spike']]['Volume'], color='green', marker='^', label='Spike')
ax3.set_title('Volume Analysis')
ax3.legend()

plt.tight_layout()
plt.show()