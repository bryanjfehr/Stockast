#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This file contains CRUD (Create, Read, Update, Delete) operations for stock data models."""

# Standard library imports
from typing import List

# Third-party imports
from sqlalchemy import desc, asc, func
from sqlalchemy.orm import Session

# Local application imports
from app.models.stock_data import StockData
from app.schemas.stock import StockDataCreate


def get_active_stocks(db: Session, limit: int = 50) -> List[StockData]:
    """
    Retrieves a list of the most active stocks from the database.

    This function first identifies the most recent data entry for each stock symbol,
    and then sorts these latest entries by trading volume in descending order.

    Args:
        db (Session): The database session.
        limit (int): The maximum number of active stocks to return.

    Returns:
        List[StockData]: A list of StockData objects representing the most active stocks.
    """
    # Create a subquery to find the latest entry for each stock symbol.
    # It partitions the data by symbol and orders by date descending,
    # assigning a row number to each record within its partition.
    latest_entry_subquery = db.query(
        StockData.id,
        func.row_number().over(
            partition_by=StockData.symbol,
            order_by=desc(StockData.date)
        ).label('row_num')
    ).subquery('latest_entry_subquery')

    # Query the StockData table, joining with the subquery to filter for
    # only the latest entries (where row_num is 1).
    # Then, order the results by volume to find the most active stocks.
    query = db.query(StockData).join(
        latest_entry_subquery, StockData.id == latest_entry_subquery.c.id
    ).filter(
        latest_entry_subquery.c.row_num == 1
    ).order_by(
        desc(StockData.volume)
    ).limit(limit)

    return query.all()


def get_historical_data(db: Session, symbol: str) -> List[StockData]:
    """
    Retrieves all historical data points for a specific stock symbol.

    Args:
        db (Session): The database session.
        symbol (str): The stock symbol to retrieve data for.

    Returns:
        List[StockData]: A list of StockData objects for the given symbol, ordered by date.
    """
    return db.query(StockData).filter(StockData.symbol == symbol).order_by(asc(StockData.date)).all()


def create_or_update_stock_data(db: Session, *, stock_data_in: StockDataCreate) -> StockData:
    """
    Creates a new stock data record or updates an existing one.

    It checks for an existing record based on the unique combination of
    symbol and date. If found, it updates the record; otherwise, it creates a new one.

    Args:
        db (Session): The database session.
        stock_data_in (StockDataCreate): The Pydantic schema containing the stock data.

    Returns:
        StockData: The created or updated StockData object.
    """
    # Check if a record with the same symbol and date already exists.
    db_stock_data = db.query(StockData).filter(
        StockData.symbol == stock_data_in.symbol,
        StockData.date == stock_data_in.date
    ).first()

    if db_stock_data:
        # Update the existing record
        # Pydantic's .dict() can be used to get a dictionary of the model's fields
        update_data = stock_data_in.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_stock_data, key, value)
        db.add(db_stock_data)  # Mark the object as dirty, as per pseudo-code
    else:
        # Create a new record
        db_stock_data = StockData(**stock_data_in.dict())
        db.add(db_stock_data)

    db.commit()
    db.refresh(db_stock_data)
    return db_stock_data
