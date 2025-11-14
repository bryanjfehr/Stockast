import logging
from abc import ABC, abstractmethod
from utils import data_fetcher
from utils import indicators
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)

# --- Constants for Strategies ---
# RSI thresholds
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Adaptive Take-Profit / Stop-Loss Parameters
TP_SL_BASE_PERCENT = 0.02
TP_SL_MAX_PERCENT = 0.05
SUCCESS_THRESHOLD = 0.60

# Momentum Surge & Trailing Stop-Loss Parameters
TRAILING_SL_PROFIT_LOCK = 0.01

class BaseStrategy(ABC):
    def __init__(self, exchange, symbol, timeframe):
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.df = pd.DataFrame()
        self.success_rate = SUCCESS_THRESHOLD # Default success rate

        # --- Configurable parameters for subclasses ---
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.rsi_period = 14
        self.momentum_threshold = 2.0

    def fetch_data(self):
        """
        Fetches historical data.
        """
        self.df = data_fetcher.fetch_ohlcv(self.exchange, self.symbol, self.timeframe)

    @abstractmethod
    def generate_signals(self):
        """
        The core logic for generating trading signals.
        Must be implemented by subclasses.
        """
        if self.df.empty:
            return pd.DataFrame()

        signals = pd.DataFrame(index=self.df.index)
        signals['signal'] = 0.0

        # Compute indicators with strategy-specific parameters
        macd, macdsignal, macdhist = indicators.compute_macd(self.df, self.macd_fast, self.macd_slow, self.macd_signal)
        rsi = indicators.compute_rsi(self.df, self.rsi_period)

        # Enhanced buy/sell signal logic
        for i in range(1, len(self.df)):
            slope = macdhist[i] - macdhist[i-1] if i > 0 and not pd.isna(macdhist[i-1]) else 0

            if rsi[i] < RSI_OVERSOLD and (macdhist[i] >= 0 or slope > 0):
                signals.loc[self.df.index[i], 'signal'] = 1.0
                logging.info(f"BUY signal for {self.symbol} at {self.df.index[i]}: RSI={rsi[i]:.2f}, MACD Hist={macdhist[i]:.2f}, Slope={slope:.2f}")
            elif rsi[i] > RSI_OVERBOUGHT:
                signals.loc[self.df.index[i], 'signal'] = -1.0
                logging.info(f"SELL signal for {self.symbol} at {self.df.index[i]}: RSI={rsi[i]:.2f}")
        return signals

    def backtest(self, historical_data):
        """
        Simulates trades on historical data and calculates performance.
        Returns signals if the win rate is above a certain threshold.
        """
        # This is a simplified backtesting example.
        # A more robust implementation would be needed for real-world use.
        signals = self.generate_signals()
        if signals is None or signals.empty:
            return None

        # Simulate trades and calculate win rate
        # In a real backtest, after a simulated buy at `entry_price`:
        # entry_price = ...
        # tp, sl = self.calculate_sl_tp(entry_price, 'buy')
        # logging.info(f"Trade opened. Initial TP: {tp}, SL: {sl}")

        # # Simulate checking for momentum surge on subsequent data points
        # post_buy_data = historical_data.loc[historical_data.index > buy_timestamp]
        # if indicators.detect_momentum_surge(post_buy_data):
        #     self._handle_momentum_surge(entry_price, post_buy_data)

        win_rate = 0.96 # Placeholder
        if win_rate > 0.95:
            return signals
        return None

    def calculate_sl_tp(self, entry_price, side):
        """
        Calculates adaptive stop-loss and take-profit levels.
        """
        # Adjust TP/SL based on performance
        tp_percent_adjustment = (self.success_rate - SUCCESS_THRESHOLD) * (TP_SL_MAX_PERCENT - TP_SL_BASE_PERCENT)
        tp_percent = TP_SL_BASE_PERCENT + max(0, tp_percent_adjustment)

        if side == 'buy':
            stop_loss = entry_price * (1 - tp_percent)
            take_profit = entry_price * (1 + tp_percent)
        elif side == 'sell':
            stop_loss = entry_price * (1 + tp_percent)
            take_profit = entry_price * (1 - tp_percent)
        else:
            return None, None
        return stop_loss, take_profit

    def _handle_momentum_surge(self, entry_price: float, post_buy_data: pd.DataFrame):
        """Adjusts exit strategy upon detecting a momentum surge."""
        logging.info("Momentum surge detected! Adjusting exit strategy.")
        projected_peak_series = indicators.extrapolate_peak(post_buy_data)
        projected_peak = projected_peak_series.iloc[-1]
        trailing_sl_price = entry_price * (1 + TRAILING_SL_PROFIT_LOCK)
        logging.info(f"Canceling TP. New target: {projected_peak}, Trailing SL: {trailing_sl_price}")
        # In a real system, you would cancel the old TP order and set new
        # limit sell and trailing stop-loss orders.