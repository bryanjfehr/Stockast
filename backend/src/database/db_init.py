from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database file path
DB_PATH = 'sqlite:///stock_data.db'

# Create engine
engine = create_engine(DB_PATH, echo=True)

# Declarative base
Base = declarative_base()

# Define Stocks table
class Stock(Base):
    __tablename__ = 'stocks'
    symbol = Column(String, primary_key=True)
    name = Column(String)
    sector = Column(String)

# Define Stock Prices table
class StockPrice(Base):
    __tablename__ = 'stock_prices'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, ForeignKey('stocks.symbol'))
    date = Column(String)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)

# Define Watchlist table
class Watchlist(Base):
    __tablename__ = 'watchlist'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, ForeignKey('stocks.symbol'))
    added_date = Column(String)

# Define Articles table
class Article(Base):
    __tablename__ = 'articles'
    id = Column(Integer, primary_key=True)
    site = Column(String)
    date = Column(String)
    symbol = Column(String, ForeignKey('stocks.symbol'))
    title = Column(String)
    content = Column(String)
    sentiment = Column(String)
    confidence = Column(Float)
    timeline = Column(String)
    url = Column(String)

# Define Trends table
class Trend(Base):
    __tablename__ = 'trends'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, ForeignKey('stocks.symbol'))
    date = Column(String)
    indicator = Column(String)
    value = Column(Float)
    signal = Column(String)

# Create all tables
def init_db():
    Base.metadata.create_all(engine)
    print("Database initialized successfully.")

# Optional: Seed initial data (e.g., common TSX stocks)
def seed_data():
    Session = sessionmaker(bind=engine)
    session = Session()

    # Example: Add some TSX stocks
    stocks = [
        Stock(symbol='TD.TO', name='Toronto-Dominion Bank', sector='Financials'),
        Stock(symbol='SHOP.TO', name='Shopify Inc.', sector='Technology'),
    ]

    for stock in stocks:
        existing = session.query(Stock).filter_by(symbol=stock.symbol).first()
        if not existing:
            session.add(stock)

    session.commit()
    session.close()
    print("Initial data seeded successfully.")

if __name__ == "__main__":
    init_db()
    seed_data()
