import logging
import pandas as pd

# Adjust the import path based on your project structure
from strategies.short_term import ShortTermStrategy
from utils import indicators

logging.basicConfig(level=logging.INFO)

def run_strategies(exchange, symbol):
    """
    Example function to run strategies and handle post-trade logic.
    """
    logging.info(f"Running short-term strategy for {symbol} on {exchange}...")
    
    # Initialize strategies
    short_term = ShortTermStrategy(exchange, symbol, '5m')

    # Fetch data and generate signals
    short_term.fetch_data()
    signals = short_term.generate_signals()
    
    logging.info("Signals generated.")
    
    # --- Placeholder for post-trade logic ---
    # Assume a 'buy' signal was generated and a trade was executed
    buy_signal_time = signals[signals['signal'] == 1.0].index.max()
    
    if pd.notna(buy_signal_time):
        entry_price = short_term.df.loc[buy_signal_time, 'close']
        logging.info(f"Buy signal detected at {buy_signal_time} with entry price {entry_price}")
        
        # Fetch subsequent data for momentum checks
        post_trade_data = short_term.df.loc[short_term.df.index > buy_signal_time]

        if not post_trade_data.empty and indicators.detect_momentum_surge(post_trade_data):
            short_term._handle_momentum_surge(entry_price, post_trade_data)

if __name__ == "__main__":
    # This allows you to run this script directly for testing
    run_strategies(exchange='binance', symbol='BTC/USDT')