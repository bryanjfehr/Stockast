from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class Watchlist(Base):
    """
    Represents a single stock entry in a user's watchlist in the database.

    Attributes:
        id (int): The primary key for the watchlist entry.
        symbol (str): The stock symbol (e.g., 'AAPL').
        owner_id (int): The foreign key linking to the user who owns this entry.
        owner (User): The SQLAlchemy relationship to the owner User object.
    """
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    owner = relationship("User", back_populates="watchlist")
