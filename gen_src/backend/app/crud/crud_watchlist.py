# backend/app/crud/crud_watchlist.py
"""
This file contains CRUD (Create, Read, Update, Delete) operations for the
Watchlist model, which represents user watchlist items.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist
from app.schemas.watchlist import WatchlistCreate


class CRUDWatchlist:
    """
    CRUD operations for user watchlist items.
    """

    def get_multi_by_owner(self, db: Session, *, owner_id: int) -> List[Watchlist]:
        """
        Retrieves all watchlist items for a specific owner.

        :param db: The database session.
        :param owner_id: The ID of the owner.
        :return: A list of watchlist items.
        """
        return db.query(Watchlist).filter(Watchlist.owner_id == owner_id).all()

    def get_by_owner_and_symbol(
        self, db: Session, *, owner_id: int, symbol: str
    ) -> Optional[Watchlist]:
        """
        Retrieves a single watchlist item for an owner by stock symbol.

        :param db: The database session.
        :param owner_id: The ID of the owner.
        :param symbol: The stock symbol.
        :return: The watchlist item or None if not found.
        """
        return (
            db.query(Watchlist)
            .filter(Watchlist.owner_id == owner_id, Watchlist.symbol == symbol)
            .first()
        )

    def create_with_owner(
        self, db: Session, *, obj_in: WatchlistCreate, owner_id: int
    ) -> Watchlist:
        """
        Creates a new watchlist item associated with an owner.

        :param db: The database session.
        :param obj_in: The data for the new watchlist item.
        :param owner_id: The ID of the owner.
        :return: The newly created watchlist item.
        """
        db_obj = Watchlist(symbol=obj_in.symbol, owner_id=owner_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[Watchlist]:
        """
        Deletes a watchlist item from the database by its ID.

        :param db: The database session.
        :param id: The ID of the watchlist item to delete.
        :return: The deleted watchlist item or None if not found.
        """
        obj = db.query(Watchlist).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj


watchlist = CRUDWatchlist()
