import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def compute_sentiment_indicator(df: pd.DataFrame, bullish_col='bullish_pct', bearish_col='bearish_pct', ema_period=5):
    """Transform sentiment to 0-100 oscillator."""
    df = df.copy()
    df['net_sentiment'] = (df[bullish_col] - df[bearish_col]) / 2 + 50  # -50 to +50 → 0-100
    df['net_sentiment'] = np.clip(df['net_sentiment'], 0, 100)
    df['sentiment_ema'] = df['net_sentiment'].ewm(span=ema_period).mean()  # Smooth
    return df

def test_leading_projection(df: pd.DataFrame, price_col='price', lag_days=1):
    """Test if sentiment leads price; project next 7 days if corr >0.2."""
    df['price_change'] = df[price_col].pct_change() * 100
    df['price_change_lead'] = df['price_change'].shift(-lag_days)  # Sentiment(t) → change(t+lag)
    corr = df['sentiment_ema'].corr(df['price_change_lead'].dropna())
    
    if corr > 0.2:
        # Train regression
        valid_idx = df.dropna().index
        X = df.loc[valid_idx, 'sentiment_ema'].values.reshape(-1, 1)
        y = df.loc[valid_idx, price_col].values
        model = LinearRegression().fit(X, y)
        
        # Project: Assume sentiment trends (e.g., +2% daily growth)
        future_days = 7
        future_sentiment = np.linspace(
            df['sentiment_ema'].iloc[-1], 
            df['sentiment_ema'].iloc[-1] * 1.02**future_days, 
            future_days
        )
        future_prices = model.predict(future_sentiment.reshape(-1, 1))
        
        future_df = pd.DataFrame({
            'date': pd.date_range(df.index[-1] + timedelta(days=1), periods=future_days),
            'projected_sentiment': future_sentiment,
            'projected_price': future_prices
        })
        return corr, future_df
    else:
        return corr, None

def plot_sentiment_projection(df: pd.DataFrame, projection=None):
    """Plot price candles (simplified line) + sentiment subchart + projection."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # Price chart
    ax1.plot(df.index, df['price'], label='BTC Price', color='blue', linewidth=2)
    ax1.set_ylabel('Price ($)')
    ax1.set_title('BTC Price with Sentiment Projection')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    if projection is not None:
        ax1.plot(projection['date'], projection['projected_price'], 
                color='red', linestyle='--', marker='o', label='Projected Price')
    
    # Sentiment oscillator
    ax2.plot(df.index, df['sentiment_ema'], label='Sentiment EMA (0-100)', color='green', linewidth=2)
    ax2.axhline(70, color='red', linestyle='--', alpha=0.7, label='Overbought (70)')
    ax2.axhline(30, color='orange', linestyle='--', alpha=0.7, label='Oversold (30)')
    ax2.set_ylabel('Sentiment %')
    ax2.set_xlabel('Date')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    if projection is not None:
        ax2.plot(projection['date'], projection['projected_sentiment'], 
                color='orange', linestyle='--', marker='s', label='Projected Sentiment')
    
    plt.tight_layout()
    plt.show()  # Or savefig('sentiment_chart.png')

# Example Usage (with sample LunarCrush data)
sample_data = pd.DataFrame({
    'date': pd.date_range('2025-11-01', periods=10),
    'price': np.random.normal(65000, 2000, 10).cumsum() + 60000,  # Simulated BTC
    'bullish_pct': np.random.uniform(40, 70, 10),
    'bearish_pct': np.random.uniform(20, 50, 10)
})
df = compute_sentiment_indicator(sample_data)
corr, proj = test_leading_projection(df)
plot_sentiment_projection(df, proj)
print(f"Leading Correlation: {corr:.3f}")
if proj is not None:
    print("Projection:\n", proj)