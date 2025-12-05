import pandas as pd
import numpy as np
from utils import indicators

def test_compute_macd():
    df = pd.DataFrame({
        'close': np.random.random(100)
    })
    macd, macdsignal, macdhist = indicators.compute_macd(df)
    assert len(macd) == len(df)
    assert len(macdsignal) == len(df)
    assert len(macdhist) == len(df)

def test_compute_rsi():
    df = pd.DataFrame({
        'close': np.random.random(100)
    })
    rsi = indicators.compute_rsi(df)
    assert len(rsi) == len(df)

def test_compute_kdj():
    df = pd.DataFrame({
        'low': np.random.random(100),
        'high': np.random.random(100),
        'close': np.random.random(100)
    })
    k, d, j = indicators.compute_kdj(df)
    assert len(k) == len(df)
    assert len(d) == len(df)
    assert len(j) == len(df)

def test_compute_volume_sma():
    df = pd.DataFrame({
        'volume': np.random.random(100)
    })
    volume_sma = indicators.compute_volume_sma(df)
    assert len(volume_sma) == len(df)
