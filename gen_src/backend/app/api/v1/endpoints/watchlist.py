import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[schemas.Watchlist])
def read_watchlist(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve the watchlist for the current authenticated user.
    """
    logger.info(f"Fetching watchlist for user: {current_user.email}")
    watchlist = crud.watchlist.get_multi_by_owner(db=db, owner_id=current_user.id)
    return watchlist


@router.post("/", response_model=schemas.Watchlist, status_code=status.HTTP_201_CREATED)
def add_stock_to_watchlist(
    *,
    db: Session = Depends(deps.get_db),
    watchlist_in: schemas.WatchlistCreate,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Add a stock to the current user's watchlist.
    """
    logger.info(f"User {current_user.email} attempting to add stock {watchlist_in.symbol} to watchlist.")
    existing_item = crud.watchlist.get_by_owner_and_symbol(
        db=db, owner_id=current_user.id, symbol=watchlist_in.symbol
    )
    if existing_item:
        logger.warning(
            f"Stock {watchlist_in.symbol} already in watchlist for user {current_user.email}."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock already in watchlist",
        )

    watchlist_item = crud.watchlist.create_with_owner(
        db=db, obj_in=watchlist_in, owner_id=current_user.id
    )
    logger.info(
        f"Successfully added stock {watchlist_in.symbol} to watchlist for user {current_user.email}."
    )
    return watchlist_item


@router.delete("/{symbol}", response_model=schemas.Msg)
def remove_stock_from_watchlist(
    symbol: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Remove a stock from the current user's watchlist by symbol.
    """
    logger.info(
        f"User {current_user.email} attempting to remove stock {symbol} from watchlist."
    )
    watchlist_item = crud.watchlist.get_by_owner_and_symbol(
        db=db, owner_id=current_user.id, symbol=symbol.upper()
    )

    if not watchlist_item:
        logger.warning(
            f"Stock {symbol} not found in watchlist for user {current_user.email}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock not found in watchlist",
        )

    crud.watchlist.remove(db=db, id=watchlist_item.id)
    logger.info(
        f"Successfully removed stock {symbol} from watchlist for user {current_user.email}."
    )
    return {"message": "Stock removed from watchlist successfully"}
