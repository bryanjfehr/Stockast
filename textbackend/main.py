import logging
from strategies.short_term import ShortTermStrategy
from strategies.medium_term import MediumTermStrategy
from strategies.long_term import LongTermStrategy
from utils import data_fetcher, indicators

logging.basicConfig(level=logging.INFO)

def run_strategies(exchange, symbol):
    """
    Example function to run strategies and handle post-trade logic.
    """
    # Initialize strategies
    short_term = ShortTermStrategy(exchange, symbol, '5m')

    # Fetch data and generate signals
    short_term.fetch_data()
    signals = short_term.generate_signals()
    
    # --- Placeholder for post-trade logic ---
    # Assume a 'buy' signal was generated and a trade was executed
    buy_signal_time = signals[signals['signal'] == 1.0].index.max()
    
    if pd.notna(buy_signal_time):
        entry_price = short_term.df.loc[buy_signal_time, 'close']
        
        # Fetch subsequent data for momentum checks
        post_trade_data = short_term.df.loc[short_term.df.index > buy_signal_time]

        if not post_trade_data.empty and indicators.detect_momentum_surge(post_trade_data):
            short_term._handle_momentum_surge(entry_price, post_trade_data)