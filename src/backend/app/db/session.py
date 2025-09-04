from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# The database URL is retrieved from the application settings.
# The `pool_pre_ping` argument enables a feature that tests connections for liveness
# before they are handed off from the connection pool.
# The `connect_args` is necessary for SQLite to allow it to be used by multiple threads,
# which is the case in a web application framework like FastAPI.
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),  # Use str() for compatibility with Pydantic types
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in str(settings.SQLALCHEMY_DATABASE_URI) else {}
)

# The sessionmaker factory generates new Session objects when called.
# autocommit=False and autoflush=False are standard settings for using SQLAlchemy
# sessions with a web framework, as the transaction lifecycle is managed explicitly.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency to get a database session.

    Yields a SQLAlchemy session that is automatically closed after the request
    is processed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
