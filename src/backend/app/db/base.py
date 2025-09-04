# backend/app/db/base.py

"""
This module defines the declarative base for all SQLAlchemy models and ensures
all models are imported for metadata registration before the application starts.
This is crucial for tools like Alembic to detect all tables.
"""

# SQLAlchemy's declarative system needs a base class from which all mapped classes should inherit.
from sqlalchemy.ext.declarative import declarative_base

# The following imports are necessary to ensure that all model classes are registered
# with SQLAlchemy's metadata before the application needs them. The '# noqa: F401'
# comments are used to suppress linter warnings about unused imports, as their
# primary purpose here is the side effect of registration.

from app.models.user import User  # noqa: F401
from app.models.watchlist import Watchlist  # noqa: F401
from app.models.stock_data import StockData  # noqa: F401
from app.models.simulation import Simulation, Trade  # noqa: F401
from app.models.article import Article  # noqa: F401

# Create the declarative base class. All ORM models in the application will inherit from this class.
Base = declarative_base()
