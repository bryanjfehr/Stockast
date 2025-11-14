from fastapi import APIRouter, HTTPException
from strategies.short_term import ShortTermStrategy
# Assume other necessary imports for your FastAPI app

router = APIRouter()

# In a real app, you would have a way to access active trades/signals
# This is a simplified placeholder.
ACTIVE_TRADES = {} 

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