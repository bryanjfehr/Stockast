from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

import logging
# Assuming you have these utility functions and strategy classes
# These imports are hypothetical and should be adjusted to your project structure.
# from strategies.main_runner import run_all_strategies
from strategies.utils.sentiment_tracker import get_daily_sentiment_trend, fetch_top_coins
from api.mexc import MexcAPI
from db.database import SessionLocal
from strategies.short_term import ShortTermStrategy

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# --- Placeholder for DB dependency ---
# In a real app, you would have a dependency injection system for your database.
def get_db():
    """Dependency to get a DB session for each request."""
    try:
        db = SessionLocal()
        yield db
    finally:
        if db:
            db.close()

async def get_exchange_client(request: Request):
    """Dependency to get an authenticated MEXC API client from request headers."""
    api_key = request.headers.get('X-Exchange-Api-Key')
    api_secret = request.headers.get('X-Exchange-Api-Secret')

    if not api_key or not api_secret:
        raise HTTPException(status_code=400, detail="X-Exchange-Api-Key and X-Exchange-Api-Secret headers are required.")

    mexc_client = None
    try:
        # The creation of the client object itself is synchronous, but we do it
        # inside the async function. The network calls will be async.
        logger.info("get_exchange_client: Creating MexcAPI client...")
        mexc_client = MexcAPI(api_key=api_key, secret=api_secret)
        if not mexc_client.exchange:
            logger.error("get_exchange_client: MexcAPI client initialization failed (no exchange object).")
            raise HTTPException(status_code=401, detail="Authentication failed: Could not initialize exchange client.")
    except Exception as e:
        logger.error(f"get_exchange_client: Exception during MexcAPI creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating MEXC client: {str(e)}")

    try:
        yield mexc_client
    finally:
        if mexc_client and mexc_client.exchange:
            await mexc_client.exchange.close()

# In a real app, you would have a way to access active trades/signals
# This is a simplified placeholder.
ACTIVE_TRADES = {} 

@router.post("/calibrate", status_code=status.HTTP_200_OK)
async def calibrate_bot_endpoint(mexc_client: MexcAPI = Depends(get_exchange_client)): # type: ignore
    """
    Endpoint to perform initial bot calibration by validating API keys.
    It expects 'X-Exchange-Api-Key' and 'X-Exchange-Api-Secret' in the headers.
    """
    try:
        logger.info("calibrate_bot_endpoint: Attempting to fetch balances for calibration...")
        # fetch_balances is now async
        await mexc_client.fetch_balances()
        logger.info("calibrate_bot_endpoint: Calibration successful.")
        return {"status": "calibration_successful", "message": "API keys are valid."}
    except Exception as e:
        logger.error(f"calibrate_bot_endpoint: Calibration failed during fetch_balances: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@router.get("/account/balance")
async def get_account_balance(mexc_client: MexcAPI = Depends(get_exchange_client)): # type: ignore
    """
    Fetches the user's account balance from the exchange.
    """
    try:
        logger.info("get_account_balance: Fetching account balance...")
        balance_data = await mexc_client.fetch_balances() # This is a ccxt object
        
        # The raw ccxt object is complex. We need to parse it into a simple list
        # of assets with non-zero balances for the frontend.
        parsed_balances = []
        if 'info' in balance_data and 'balances' in balance_data['info']:
            for item in balance_data['info']['balances']:
                free_balance = float(item.get('free', 0))
                if free_balance > 0:
                    parsed_balances.append({'asset': item['asset'], 'free': free_balance})
        
        logger.info(f"get_account_balance: Parsed and returning balances: {parsed_balances}")
        return parsed_balances
    except Exception as e:
        logger.error(f"get_account_balance: Failed to fetch balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch account balance: {str(e)}")

@router.post("/run-strategies", status_code=status.HTTP_202_ACCEPTED)
async def run_strategies_endpoint():
    """Endpoint to trigger a one-off strategy execution cycle."""
    # run_all_strategies() # This would be a non-blocking call in a real app
    return {"status": "strategy_run_triggered"}

@router.post("/signals/{symbol}/details")
def get_signal_details(symbol: str, entry_price: float, side: str):
    """
    For a given symbol and trade entry, calculates and returns the
    dynamically adjusted Take-Profit and Stop-Loss levels.
    """
    # We'll use a strategy instance to access its calculation logic.
    # In a real app, you might fetch the strategy associated with the trade.
    strategy = ShortTermStrategy(exchange=None, symbol=symbol, timeframe='5m')

    # You might want to load the strategy's actual success rate from a DB
    # strategy.success_rate = fetch_success_rate_from_db(strategy_name)

    tp, sl = strategy.calculate_sl_tp(entry_price, side)

    if tp is None:
        raise HTTPException(status_code=400, detail="Invalid side provided.")

    return {"symbol": symbol, "take_profit": tp, "stop_loss": sl}

@router.get("/ohlcv/{symbol:path}")
async def get_ohlcv_data(symbol: str, timeframe: str = '1h', limit: int = 100, mexc_client: MexcAPI = Depends(get_exchange_client)): # type: ignore
    """
    Fetches historical OHLCV data for a given symbol.
    The `:path` in the route allows symbols like 'BTC/USDT' to be passed correctly.
    """
    try:
        logger.info(f"get_ohlcv_data: Fetching OHLCV for {symbol}...")
        # The ccxt library is async, so we need to use await here.
        ohlcv = await mexc_client.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit) # type: ignore
        # Log the first data point to confirm structure
        logger.info(f"get_ohlcv_data: Successfully fetched {len(ohlcv)} OHLCV points. First point: {ohlcv[0] if ohlcv else 'N/A'}")
        # The ohlcv data is already a list of lists, which is JSON serializable.
        return ohlcv
    except HTTPException:
        raise # Re-raise HTTP exceptions from the dependency
    except Exception as e:
        logger.error(f"get_ohlcv_data: Failed to fetch OHLCV for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch OHLCV data: {str(e)}")

@router.get("/sentiment")
async def get_general_sentiment(request: Request, db: Session = Depends(get_db)):
    """
    Fetches general market sentiment.
    This fulfills the requirement from App.tsx's background fetch.
    """
    # The frontend now sends the Santiment key in the headers.
    # We extract it here to pass to our sentiment functions.
    santiment_key = request.headers.get('X-Santiment-Api-Key')
    if not santiment_key:
        logger.error("get_general_sentiment: X-Santiment-Api-Key header is missing.")
        raise HTTPException(status_code=400, detail="X-Santiment-Api-Key header is required.")

    try:
        # Fetch the top coins and then get their sentiment trends.
        # We run the synchronous sanpy calls in a threadpool to avoid blocking the server.
        top_symbols = await run_in_threadpool(fetch_top_coins, santiment_key) # type: ignore
        trends = {}
        # Limit to the top 10 for a quick overview to avoid long API calls
        for symbol in top_symbols[:10]:
            trend_data = await run_in_threadpool(get_daily_sentiment_trend, db, symbol) # type: ignore
            if trend_data and 'live_24h' in trend_data:
                trends[symbol] = trend_data['live_24h']
        return {'top_sentiment': trends}
    except Exception as e:
        logger.error(f"get_general_sentiment: An exception occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/{symbol}")
async def get_symbol_sentiment(symbol: str, db: Session = Depends(get_db)):
    """Fetches detailed sentiment for a specific symbol."""
    # Also run this synchronous DB call in the threadpool
    trend = await run_in_threadpool(get_daily_sentiment_trend, db, symbol.upper()) # type: ignore
    if not trend:
        raise HTTPException(status_code=404, detail=f"Sentiment data not found for symbol: {symbol}")
    return trend