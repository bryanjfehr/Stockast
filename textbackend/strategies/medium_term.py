import pandas as pd
from typing import Dict, Any
from .base import BaseStrategy
from ..config import ENTRY_EXIT_TIMEFRAME_MEDIUM

class MediumTermStrategy(BaseStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol, ENTRY_EXIT_TIMEFRAME_MEDIUM)

    def generate_signals(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.DataFrame:
        """
        Generates trading signals for a medium-term strategy.
        - Buy when K line crosses above D line and both are below 80.
        - Sell when K line crosses below D line and both are above 20.
        """
        signals = []
        k = indicators['k']
        d = indicators['d']

        min_len = min(len(k), len(d))

        for i in range(1, min_len):
            # Buy signal
            if k[i] > d[i] and k[i-1] <= d[i-1] and k[i] < 80 and d[i] < 80:
                signals.append({'timestamp': df['timestamp'].iloc[i], 'signal': 'buy'})
            # Sell signal
            elif k[i] < d[i] and k[i-1] >= d[i-1] and k[i] > 20 and d[i] > 20:
                signals.append({'timestamp': df['timestamp'].iloc[i], 'signal': 'sell'})
        
        return pd.DataFrame(signals)
