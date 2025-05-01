import time
import logging
import talib
import numpy as np
from database.db_operations import get_stock_prices, get_all_symbols
from alerting.notification import send_alert
from config import config

# Configure logging for monitoring and debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# User-configurable settings for day trading (short timeframes)
INDICATOR_SETTINGS = {
    'MA_SHORT_PERIOD': 5,    # 5-period MA for quick trends
    'MA_LONG_PERIOD': 15,    # 15-period MA for confirmation
    'RSI_PERIOD': 14,        # Standard RSI period
    'RSI_OVERBOUGHT': 70,    # Sell signal threshold
    'RSI_OVERSOLD': 30,      # Buy signal threshold
    'BB_PERIOD': 20,         # Bollinger Bands period
    'BB_NBDEV_UP': 2,        # Upper band deviation
    'BB_NBDEV_DOWN': 2       # Lower band deviation
}

def generate_signals(symbol, prices):
    """
    Generate buy/sell signals using short-term indicators optimized for day trading.
    
    Args:
        symbol (str): Stock symbol
        prices (list): List of StockPrice objects with close prices and timestamps
    
    Returns:
        list: List of signal dictionaries with date, signal type, price, and indicator
    """
    if not prices or len(prices) < max(INDICATOR_SETTINGS.values()):
        logging.warning(f"Insufficient data for {symbol}")
        return []

    closes = np.array([price.close for price in prices], dtype=np.float64)
    dates = [price.date for price in prices]

    signals = []

    # Moving Average Crossover (fast response for day trading)
    ma_short = talib.SMA(closes, timeperiod=INDICATOR_SETTINGS['MA_SHORT_PERIOD'])
    ma_long = talib.SMA(closes, timeperiod=INDICATOR_SETTINGS['MA_LONG_PERIOD'])
    if ma_short[-1] > ma_long[-1] and ma_short[-2] <= ma_long[-2]:
        signals.append({'date': dates[-1], 'signal': 'BUY', 'price': closes[-1], 'indicator': 'MA Crossover'})
    elif ma_short[-1] < ma_long[-1] and ma_short[-2] >= ma_long[-2]:
        signals.append({'date': dates[-1], 'signal': 'SELL', 'price': closes[-1], 'indicator': 'MA Crossover'})

    # RSI (identify overbought/oversold conditions)
    rsi = talib.RSI(closes, timeperiod=INDICATOR_SETTINGS['RSI_PERIOD'])
    if rsi[-1] < INDICATOR_SETTINGS['RSI_OVERSOLD']:
        signals.append({'date': dates[-1], 'signal': 'BUY', 'price': closes[-1], 'indicator': 'RSI Oversold'})
    elif rsi[-1] > INDICATOR_SETTINGS['RSI_OVERBOUGHT']:
        signals.append({'date': dates[-1], 'signal': 'SELL', 'price': closes[-1], 'indicator': 'RSI Overbought'})

    # Bollinger Bands (volatility-based signals)
    upper, middle, lower = talib.BBANDS(closes, timeperiod=INDICATOR_SETTINGS['BB_PERIOD'],
                                        nbdevup=INDICATOR_SETTINGS['BB_NBDEV_UP'],
                                        nbdevdn=INDICATOR_SETTINGS['BB_NBDEV_DOWN'])
    if closes[-1] < lower[-1]:
        signals.append({'date': dates[-1], 'signal': 'BUY', 'price': closes[-1], 'indicator': 'BB Lower Band'})
    elif closes[-1] > upper[-1]:
        signals.append({'date': dates[-1], 'signal': 'SELL', 'price': closes[-1], 'indicator': 'BB Upper Band'})

    return signals

def process_stock(symbol):
    """
    Process a single stock, generate signals, and send alerts immediately.
    
    Args:
        symbol (str): Stock symbol to process
    """
    try:
        # Fetch recent prices (e.g., last 30 minutes of 1-minute data for day trading)
        prices = get_stock_prices(symbol, timeframe='1min', limit=30)
        signals = generate_signals(symbol, prices)
        for signal in signals:
            message = f"{signal['indicator']} signal for {symbol}: {signal['signal']} at {signal['price']}"
            send_alert(message)  # Immediate notification (e.g., SMS or in-app)
            logging.info(f"Alert sent: {message}")
    except Exception as e:
        logging.error(f"Error processing {symbol}: {str(e)}")

def real_time_monitor():
    """
    Continuously monitor all stocks in real-time for day trading signals.
    """
    symbols = get_all_symbols()  # Fetch watchlist dynamically
    while True:
        try:
            for symbol in symbols:
                process_stock(symbol)
            time.sleep(config.REAL_TIME_INTERVAL)  # e.g., 60 seconds for frequent checks
        except KeyboardInterrupt:
            logging.info("Real-time monitoring stopped by user")
            break
        except Exception as e:
            logging.error(f"Error in real-time loop: {str(e)}")
            time.sleep(5)  # Brief pause before retrying

if __name__ == "__main__":
    # Start real-time monitoring for day trading
    logging.info("Starting real-time alert generator for day trading")
    real_time_monitor()