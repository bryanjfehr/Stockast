import datetime
from typing import Optional

from pydantic import BaseModel


class StockDataBase(BaseModel):
    """
    Base schema for stock data, containing common fields.
    Fields are optional to accommodate different data sources and use cases.
    """
    symbol: str
    date: datetime.date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    price: Optional[float] = None
    change: Optional[float] = None
    percent_change: Optional[float] = None


class StockDataCreate(StockDataBase):
    """
    Schema for creating a new stock data record in the database.
    Inherits all fields from StockDataBase.
    """
    pass


class StockData(StockDataBase):
    """
    Schema for representing a stock data record retrieved from the database.
    Includes the database ID and is configured for ORM mode.
    """
    id: int

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class StockDataHistorical(BaseModel):
    """
    Schema specifically for historical stock data points (OHLCV).
    Fields are non-optional as they are expected for historical analysis.
    """
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: int

    class Config:
        """Pydantic configuration."""
        from_attributes = True
