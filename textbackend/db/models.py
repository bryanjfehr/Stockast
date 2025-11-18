from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Symbol(Base):
    __tablename__ = "symbols"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    ohlcv_data = relationship("OHLCV", back_populates="symbol")

class OHLCV(Base):
    __tablename__ = "ohlcv"
    id = Column(Integer, primary_key=True, index=True)
    symbol_id = Column(Integer, ForeignKey("symbols.id"))
    symbol = relationship("Symbol", back_populates="ohlcv_data")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    strategy = Column(String)
    direction = Column(String)  # "long" or "short"
    entry_price = Column(Float)
    exit_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    status = Column(String)  # "open", "closed"
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    strategy = Column(String)
    win_rate = Column(Float)
    signal_type = Column(String) # "buy", "sell"
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class SocialMetric(Base):
    __tablename__ = "social_metrics"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    date = Column(DateTime, index=True)
    mentions = Column(Float)
    bullish_pct = Column(Float)
    bearish_pct = Column(Float)
    neutral_pct = Column(Float)
    net_sentiment = Column(Float) # bullish - bearish
