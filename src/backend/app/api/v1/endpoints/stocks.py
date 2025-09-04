# DESCRIPTION: This file defines the API endpoints for retrieving stock data.

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import crud_stock
from app.db.session import get_db
from app.schemas import stock as stock_schema

# Initialize an instance of APIRouter with a prefix '/stocks' and a tag 'stocks'.
router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
)


@router.get("/active", response_model=List[stock_schema.StockData])
def read_active_stocks(db: Session = Depends(get_db)):
    """
    Retrieves the 50 most active TSX stocks.

    Args:
        db (Session): The database session, injected by FastAPI.

    Returns:
        List[stock_schema.StockData]: A list of the 50 most active stocks.
    """
    active_stocks = crud_stock.get_active_stocks(db=db, limit=50)
    return active_stocks


@router.get("/{symbol}/historical", response_model=List[stock_schema.StockDataHistorical])
def read_historical_stock_data(symbol: str, db: Session = Depends(get_db)):
    """
    Retrieves historical daily data for a given stock symbol.

    Args:
        symbol (str): The stock symbol to retrieve historical data for.
        db (Session): The database session, injected by FastAPI.

    Raises:
        HTTPException: If no data is found for the given symbol (status code 404).

    Returns:
        List[stock_schema.StockDataHistorical]: A list of historical data points for the stock.
    """
    historical_data = crud_stock.get_historical_data(db=db, symbol=symbol)
    if not historical_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Historical data not found for symbol {symbol}",
        )
    return historical_data
