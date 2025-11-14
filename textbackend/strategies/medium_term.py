import logging
from .base import BaseStrategy

logging.basicConfig(level=logging.INFO)

class MediumTerm(BaseStrategy):
    def __init__(self, exchange, symbol):
        super().__init__(exchange, symbol, timeframe='1h')

    def generate_signals(self):
        """
        Generates signals for medium-term trading.
        Focuses on 1-2 day holds and longer-term indicators.
        """
        self.fetch_data()
        self.compute_indicators()

        # Example Signal Logic (to be refined)
        # Buy signal: MACD crosses above signal line, RSI is not overbought
        if (self.df['macd'].iloc[-1] > self.df['macdsignal'].iloc[-1] and
                self.df['macd'].iloc[-2] <= self.df['macdsignal'].iloc[-2] and
                self.df['rsi'].iloc[-1] < 70):
            return {'signal': 'buy', 'price': self.df['close'].iloc[-1]}

        # Sell signal: MACD crosses below signal line, RSI is not oversold
        if (self.df['macd'].iloc[-1] < self.df['macdsignal'].iloc[-1] and
                self.df['macd'].iloc[-2] >= self.df['macdsignal'].iloc[-2] and
                self.df['rsi'].iloc[-1] > 30):
            return {'signal': 'sell', 'price': self.df['close'].iloc[-1]}

        return None