# backend/app/models/user.py

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

# The dependency list specifies `app.db.base.Base`, which implies the Base class
# is defined in a file `app/db/base.py`.
# This is a common pattern in projects using a shared declarative base.
from app.db.base_class import Base


class User(Base):
    """
    SQLAlchemy model for a user.
    Represents the 'users' table in the database.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    vertex_ai_api_key = Column(String, nullable=True)

    # Relationships are defined using string names for the related classes
    # to avoid circular import issues at runtime, which is a best practice.
    watchlist = relationship("Watchlist", back_populates="owner", cascade="all, delete-orphan")
    simulations = relationship("Simulation", back_populates="owner", cascade="all, delete-orphan")
