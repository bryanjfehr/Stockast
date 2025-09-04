import datetime
import typing

from sqlalchemy import Column, DateTime, Integer, JSON, String

from app.db.base import Base


class Article(Base):
    """
    SQLAlchemy model for the 'articles' table.

    This table stores information about news articles related to stocks.
    """
    __tablename__ = "articles"

    id: int = Column(Integer, primary_key=True, index=True)
    title: str = Column(String, nullable=False)
    url: str = Column(String, unique=True, nullable=False, index=True)
    source: str = Column(String, nullable=False)
    published_at: datetime.datetime = Column(DateTime, nullable=False, index=True)
    symbols: typing.Optional[typing.List[str]] = Column(JSON, nullable=True)
