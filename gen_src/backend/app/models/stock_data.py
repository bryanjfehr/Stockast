# backend/app/models/stock_data.py
"""This module defines the SQLAlchemy model for stock data."""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Float,
    Integer,
    String,
    UniqueConstraint,
)

# In a typical FastAPI/SQLAlchemy setup, a `Base` class is created using
# `declarative_base()` and shared across all models. This import assumes
# that `app.db.base.py` provides this `Base` object, as specified in the
# project's dependency information.
from app.db.base_class import Base


class StockData(Base):
    """Represents historical and daily stock data in the database.

    This model maps to the 'stock_data' table and includes columns for
    standard stock metrics like open, high, low, close, volume, and price,
    associated with a specific symbol and date.
    """

    __tablename__ = "stock_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)

    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(BigInteger, nullable=True)

    # Fields for daily summary/quote data
    price = Column(Float, nullable=True)
    change = Column(Float, nullable=True)
    percent_change = Column(Float, nullable=True)

    # Enforce that each stock can only have one entry per day.
    __table_args__ = (UniqueConstraint("symbol", "date", name="_symbol_date_uc"),)
