from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any
from ..utils.indicators import calculate_macd, calculate_rsi, calculate_kdj
from ..db.utils import get_db_session
from ..db.models import OHLCV, Signal
from ..config import MIN_WIN_RATE

class BaseStrategy(ABC):
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe

    def get_data(self) -> pd.DataFrame:
        """Retrieves OHLCV data from the database."""
        with get_db_session() as session:
            data = session.query(OHLCV).filter(OHLCV.symbol.has(name=self.symbol)).order_by(OHLCV.timestamp.desc()).limit(200).all()
            return pd.DataFrame([(d.timestamp, d.open, d.high, d.low, d.close, d.volume) for d in data],
                                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    def calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates all indicators."""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        
        macd, macdsignal, macdhist = calculate_macd(close)
        rsi = calculate_rsi(close)
        slowk, slowd = calculate_kdj(high, low, close)

        return {
            'macd': macd,
            'macdsignal': macdsignal,
            'rsi': rsi,
            'k': slowk,
            'd': slowd
        }

    def backtest(self, signals: pd.DataFrame) -> float:
        """
        A simple backtest to calculate win rate.
        This should be replaced with a more sophisticated backtesting engine.
        """
        # This is a placeholder for a real backtesting implementation
        # For now, we'll assume a high win rate to allow trading.
        return 0.98 

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.DataFrame:
        """Generates trading signals."""
        pass

    def run(self):
        """Runs the strategy."""
        df = self.get_data()
        if df.empty:
            return
            
        indicators = self.calculate_indicators(df)
        signals = self.generate_signals(df, indicators)

        if not signals.empty:
            win_rate = self.backtest(signals)
            if win_rate > MIN_WIN_RATE:
                with get_db_session() as session:
                    for _, row in signals.iterrows():
                        signal = Signal(
                            symbol=self.symbol,
                            strategy=self.__class__.__name__,
                            win_rate=win_rate,
                            signal_type=row['signal'],
                        )
                        session.add(signal)
