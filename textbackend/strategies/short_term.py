import pandas as pd
from typing import Dict, Any
from .base import BaseStrategy
from ..config import ENTRY_EXIT_TIMEFRAME_SHORT

class ShortTermStrategy(BaseStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol, ENTRY_EXIT_TIMEFRAME_SHORT)

    def generate_signals(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.DataFrame:
        """
        Generates trading signals for a short-term strategy.
        - Buy when MACD crosses above signal line and RSI is below 70.
        - Sell when MACD crosses below signal line and RSI is above 30.
        """
        signals = []
        macd = indicators['macd']
        macdsignal = indicators['macdsignal']
        rsi = indicators['rsi']

        # Ensure all indicators have the same length
        min_len = min(len(macd), len(macdsignal), len(rsi))
        
        for i in range(1, min_len):
            # Buy signal
            if macd[i] > macdsignal[i] and macd[i-1] <= macdsignal[i-1] and rsi[i] < 70:
                signals.append({'timestamp': df['timestamp'].iloc[i], 'signal': 'buy'})
            # Sell signal
            elif macd[i] < macdsignal[i] and macd[i-1] >= macdsignal[i-1] and rsi[i] > 30:
                signals.append({'timestamp': df['timestamp'].iloc[i], 'signal': 'sell'})
        
        return pd.DataFrame(signals)
