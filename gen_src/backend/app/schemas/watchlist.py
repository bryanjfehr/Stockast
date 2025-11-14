# backend/app/schemas/watchlist.py

"""
This file defines the Pydantic schemas for user watchlist items.

These schemas are used for data validation, serialization, and documentation
in the API endpoints related to watchlists.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


# Base schema for common watchlist item attributes
class WatchlistBase(BaseModel):
    """Base schema for a watchlist item, containing the stock symbol."""
    symbol: str


# Schema for creating a new watchlist item
class WatchlistCreate(WatchlistBase):
    """Schema used when adding a new stock to a user's watchlist."""
    pass


# Schema for updating an existing watchlist item
class WatchlistUpdate(WatchlistBase):
    """Schema for updating a watchlist item. All fields are optional."""
    symbol: Optional[str] = None


# Base schema for watchlist items as they are stored in the database
class WatchlistInDBBase(WatchlistBase):
    """Base schema for a watchlist item retrieved from the database, including ID and owner ID."""
    id: int
    owner_id: int

    # Pydantic V2 configuration to allow mapping from ORM models
    model_config = ConfigDict(from_attributes=True)


# Schema for returning a watchlist item from the API
class Watchlist(WatchlistInDBBase):
    """Schema representing a complete watchlist item for API responses."""
    pass
