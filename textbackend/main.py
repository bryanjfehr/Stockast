import uvicorn
from fastapi import FastAPI, Depends
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from api.mexc import MexcAPI
from db.utils import get_db_session, store_data
from db.models import Trade
from strategies.short_term import ShortTerm
from strategies.medium_term import MediumTerm
from strategies.long_term import LongTerm
from utils.data_fetcher import fetch_symbols

load_dotenv()

app = FastAPI()

# In a real application, these would be stored securely, not in-memory.
api_keys = {}

def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()

def run_strategies():
    """
    Instantiates and runs all trading strategies.
    """
    db = get_db_session()
    try:
        api_key = os.getenv("MEXC_API_KEY")
        secret = os.getenv("MEXC_SECRET_KEY")

        if not api_key or not secret:
            print("API key and secret not found. Skipping strategy run.")
            return

        mexc_api = MexcAPI(api_key, secret)
        symbols = fetch_symbols(mexc_api.exchange)
        usdt_symbols = [s for s in symbols if s.endswith('USDT')]


        for symbol in usdt_symbols[:5]: # Limiting to 5 symbols for this example
            print(f"Running strategies for {symbol}...")
            strategies = [
                ShortTerm(mexc_api.exchange, symbol),
                MediumTerm(mexc_api.exchange, symbol),
                LongTerm(mexc_api.exchange, symbol)
            ]

            for strategy in strategies:
                signal = strategy.generate_signals()
                if signal:
                    print(f"Signal generated for {symbol} using {strategy.__class__.__name__}: {signal}")
                    # In a real application, you would place an order here
                    # mexc_api.place_order(symbol, signal['signal'], 'limit', 1, signal['price'])
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_strategies, 'interval', seconds=60)
    scheduler.start()

@app.get("/symbols")
def get_symbols_endpoint():
    """
    Fetches and returns a list of symbols.
    """
    api_key = os.getenv("MEXC_API_KEY")
    secret = os.getenv("MEXC_SECRET_KEY")
    if not api_key or not secret:
        return {"error": "API key and secret not set."}
    mexc_api = MexcAPI(api_key, secret)
    return fetch_symbols(mexc_api.exchange)

@app.post("/keys")
def store_keys(api_key: str, secret: str):
    """
    Stores API keys securely. (Placeholder)
    """
    # In a real application, use a secure vault or encrypted storage.
    os.environ["MEXC_API_KEY"] = api_key
    os.environ["MEXC_SECRET_KEY"] = secret
    return {"message": "API keys stored successfully."}

@app.get("/trades")
def list_trades(db: Session = Depends(get_db)):
    """
    Lists all trades from the database.
    """
    return db.query(Trade).all()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)