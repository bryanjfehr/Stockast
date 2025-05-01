from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from db_init import engine, Stock, StockPrice, Watchlist, Article, Trend

# Create a session factory
Session = sessionmaker(bind=engine)

def add_stock(symbol, name, sector):
    """
    Adds a new stock to the stocks table.
    """
    with Session() as session:
        stock = Stock(symbol=symbol, name=name, sector=sector)
        session.add(stock)
        try:
            session.commit()
            print(f"Stock {symbol} added successfully.")
        except IntegrityError:
            print(f"Stock {symbol} already exists.")

def get_stock(symbol):
    """
    Retrieves a stock by its symbol.
    """
    with Session() as session:
        return session.query(Stock).filter_by(symbol=symbol).first()

def add_stock_price(symbol, date, open, high, low, close, volume):
    """
    Adds a new price entry for a stock.
    """
    with Session() as session:
        stock = session.query(Stock).filter_by(symbol=symbol).first()
        if not stock:
            print(f"Stock {symbol} does not exist.")
            return
        price = StockPrice(symbol=symbol, date=date, open=open, high=high, low=low, close=close, volume=volume)
        session.add(price)
        session.commit()
        print(f"Price data for {symbol} on {date} added successfully.")

def get_stock_prices(symbol, start_date, end_date):
    """
    Retrieves historical prices for a stock within a date range.
    """
    with Session() as session:
        return session.query(StockPrice).filter_by(symbol=symbol).filter(StockPrice.date.between(start_date, end_date)).all()

def add_to_watchlist(symbol, added_date):
    """
    Adds a stock to the watchlist if it's not already present.
    """
    with Session() as session:
        if session.query(Watchlist).filter_by(symbol=symbol).first():
            print(f"Stock {symbol} is already in the watchlist.")
        else:
            watchlist_entry = Watchlist(symbol=symbol, added_date=added_date)
            session.add(watchlist_entry)
            session.commit()
            print(f"Stock {symbol} added to watchlist.")

def remove_from_watchlist(symbol):
    """
    Removes a stock from the watchlist.
    """
    with Session() as session:
        entry = session.query(Watchlist).filter_by(symbol=symbol).first()
        if entry:
            session.delete(entry)
            session.commit()
            print(f"Stock {symbol} removed from watchlist.")
        else:
            print(f"Stock {symbol} not found in watchlist.")

def get_watchlist():
    """
    Retrieves all stocks in the watchlist.
    """
    with Session() as session:
        return session.query(Watchlist).all()

def add_article(site, date, symbol, title, content, sentiment, confidence, timeline, url):
    """
    Adds a new article to the articles table.
    """
    with Session() as session:
        article = Article(site=site, date=date, symbol=symbol, title=title, content=content,
                          sentiment=sentiment, confidence=confidence, timeline=timeline, url=url)
        session.add(article)
        session.commit()
        print(f"Article for {symbol} added successfully.")

def get_articles_by_symbol(symbol):
    """
    Retrieves articles related to a specific stock.
    """
    with Session() as session:
        return session.query(Article).filter_by(symbol=symbol).all()

def add_trend(symbol, date, indicator, value, signal):
    """
    Adds a new trend entry for a stock.
    """
    with Session() as session:
        stock = session.query(Stock).filter_by(symbol=symbol).first()
        if not stock:
            print(f"Stock {symbol} does not exist.")
            return
        trend = Trend(symbol=symbol, date=date, indicator=indicator, value=value, signal=signal)
        session.add(trend)
        session.commit()
        print(f"Trend data for {symbol} on {date} added successfully.")

def get_trends_by_symbol(symbol):
    """
    Retrieves trends for a specific stock.
    """
    with Session() as session:
        return session.query(Trend).filter_by(symbol=symbol).all()

def get_all_symbols():
    """
    Retrieves all stock symbols in the stocks table.
    """
    with Session() as session:
        return [stock.symbol for stock in session.query(Stock).all()]
