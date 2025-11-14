import ccxt
from typing import List, Dict, Any
from ..config import MEXC_API_KEY, MEXC_SECRET_KEY, CCXT_RECV_WINDOW

class MEXCWrapper:
    def __init__(self):
        self.exchange = ccxt.mexc({
            'apiKey': MEXC_API_KEY,
            'secret': MEXC_SECRET_KEY,
            'options': {
                'defaultType': 'spot',
                'recvWindow': CCXT_RECV_WINDOW,
            },
        })
        self.exchange.load_markets()

    def get_spot_symbols(self) -> List[str]:
        """Fetches all spot symbols from MEXC."""
        return [s for s in self.exchange.markets if self.exchange.markets[s]['spot']]

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> List[List]:
        """Fetches OHLCV data for a given symbol and timeframe."""
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    def fetch_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Fetches the order book for a given symbol."""
        return self.exchange.fetch_order_book(symbol, limit=limit)

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None):
        """Creates a trade order."""
        if order_type == 'market':
            return self.exchange.create_market_order(symbol, side, amount)
        elif order_type == 'limit':
            return self.exchange.create_limit_order(symbol, side, amount, price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

    def cancel_order(self, order_id: str, symbol: str):
        """Cancels an existing order."""
        return self.exchange.cancel_order(order_id, symbol)
