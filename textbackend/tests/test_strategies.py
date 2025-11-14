import pandas as pd
import pytest
from unittest.mock import MagicMock
from strategies.short_term import ShortTerm
from strategies.medium_term import MediumTerm
from strategies.long_term import LongTerm

@pytest.fixture
def mock_exchange():
    """
    Creates a mock exchange object.
    """
    exchange = MagicMock()
    exchange.fetch_ohlcv.return_value = [
        [1672531200000, 100, 105, 98, 102, 1000],
        [1672534800000, 102, 108, 101, 107, 1200],
        # ... add more data as needed
    ]
    return exchange

@pytest.fixture
def mock_data():
    """
    Creates a mock DataFrame for testing.
    """
    return pd.DataFrame({
        'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
        'open': [100, 102, 105],
        'high': [105, 108, 110],
        'low': [98, 100, 103],
        'close': [102, 107, 108],
        'volume': [1000, 1200, 1100]
    })

def test_short_term_strategy(mock_exchange, mock_data):
    strategy = ShortTerm(mock_exchange, 'BTC/USDT')
    strategy.df = mock_data
    strategy.compute_indicators()
    signal = strategy.generate_signals()
    # Assertions depend on the specifics of your signal generation
    assert signal is None or isinstance(signal, dict)

def test_medium_term_strategy(mock_exchange, mock_data):
    strategy = MediumTerm(mock_exchange, 'BTC/USDT')
    strategy.df = mock_data
    strategy.compute_indicators()
    signal = strategy.generate_signals()
    assert signal is None or isinstance(signal, dict)

def test_long_term_strategy(mock_exchange, mock_data):
    strategy = LongTerm(mock_exchange, 'BTC/USDT')
    strategy.df = mock_data
    strategy.compute_indicators()
    signal = strategy.generate_signals()
    assert signal is None or isinstance(signal, dict)
