import logging
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from .api.mexc import MEXCWrapper
from .utils.data_fetcher import DataFetcher
from .strategies.short_term import ShortTermStrategy
from .strategies.medium_term import MediumTermStrategy
from .strategies.long_term import LongTermStrategy
from .db.utils import get_db_session
from .db.models import Symbol, Base
from .db.utils import engine
from .config import POLLING_INTERVAL_MINUTES

logging.basicConfig(level=logging.INFO)

app = FastAPI()

mexc_wrapper = MEXCWrapper()
data_fetcher = DataFetcher(mexc_wrapper)

def run_strategies():
    """Fetches symbols and runs all trading strategies."""
    with get_db_session() as session:
        symbols = session.query(Symbol).all()
        for symbol in symbols:
            try:
                ShortTermStrategy(symbol.name).run()
                MediumTermStrategy(symbol.name).run()
                LongTermStrategy(symbol.name).run()
            except Exception as e:
                logging.error(f"Error running strategy for {symbol.name}: {e}")

@app.on_event("startup")
def startup_event():
    """Initializes the database and starts the scheduler."""
    Base.metadata.create_all(bind=engine)
    
    # Initial data fetch
    data_fetcher.fetch_and_store_symbols()
    with get_db_session() as session:
        symbols = [s.name for s in session.query(Symbol).all()]
    data_fetcher.fetch_and_store_ohlcv(symbols, "1h") # Initial fetch for trend analysis

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_strategies, 'interval', minutes=POLLING_INTERVAL_MINUTES)
    scheduler.start()
    logging.info("Scheduler started.")

@app.get("/symbols")
def get_symbols():
    """Returns a list of all available symbols."""
    with get_db_session() as session:
        return [s.name for s in session.query(Symbol).all()]

@app.get("/trades/{symbol}")
def get_trades(symbol: str):
    """Returns the trade history for a given symbol."""
    # This is a placeholder. A full implementation would query the 'trades' table.
    return {"message": f"Trade history for {symbol} is not yet implemented."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
