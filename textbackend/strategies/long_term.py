from .base import BaseStrategy
import pandas as pd

class LongTermStrategy(BaseStrategy):
    """
    A long-term strategy for position trading.
    Uses longer indicator windows (e.g., 1h+ timeframes) and requires
    stronger momentum confirmation.
    """
    def __init__(self, exchange, symbol, timeframe='1h'):
        super().__init__(exchange, symbol, timeframe)

        # --- Override parameters for long-term trading ---
        self.macd_fast = 24
        self.macd_slow = 52
        self.rsi_period = 28
        # Higher threshold to confirm major momentum shifts
        self.momentum_threshold = 2.5

    def generate_signals(self) -> pd.DataFrame:
        # Uses the signal logic from the parent BaseStrategy
        return super().generate_signals()