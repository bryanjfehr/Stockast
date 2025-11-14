import pandas as pd
from typing import Dict, Any
from .base import BaseStrategy
from ..config import ENTRY_EXIT_TIMEFRAME_LONG

class LongTermStrategy(BaseStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol, ENTRY_EXIT_TIMEFRAME_LONG)

    def generate_signals(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.DataFrame:
        """
        Generates trading signals for a long-term strategy.
        - Buy when RSI crosses above 30.
        - Sell when RSI crosses below 70.
        """
        signals = []
        rsi = indicators['rsi']

        for i in range(1, len(rsi)):
            # Buy signal
            if rsi[i] > 30 and rsi[i-1] <= 30:
                signals.append({'timestamp': df['timestamp'].iloc[i], 'signal': 'buy'})
            # Sell signal
            elif rsi[i] < 70 and rsi[i-1] >= 70:
                signals.append({'timestamp': df['timestamp'].iloc[i], 'signal': 'sell'})
        
        return pd.DataFrame(signals)
