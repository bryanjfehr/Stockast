from .base import BaseStrategy
import pandas as pd

class ShortTermStrategy(BaseStrategy):
    """
    A short-term strategy focusing on rapid momentum shifts.
    Uses shorter indicator windows (e.g., 5-15m timeframes) and is more
    sensitive to momentum surges.
    """
    def __init__(self, exchange, symbol, timeframe='5m'):
        super().__init__(exchange, symbol, timeframe)

        # --- Override parameters for short-term trading ---
        self.macd_fast = 8
        self.macd_slow = 21
        self.rsi_period = 10
        # Lower threshold for quicker detection on shorter timeframes
        self.momentum_threshold = 1.5

    def generate_signals(self) -> pd.DataFrame:
        # Uses the signal logic from the parent BaseStrategy
        return super().generate_signals()