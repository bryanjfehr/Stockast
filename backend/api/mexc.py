import logging
import time
import ccxt.async_support as ccxt

# Configure a specific logger for this module
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

class MexcAPI:
    def __init__(self, api_key: str, secret: str):
        if not api_key or not secret:
            logging.error("MexcAPI requires an api_key and secret to be provided.")
            self.exchange = None
            return
        
        # The constructor itself should not be async.
        # We will use a factory method to create an initialized instance.
        logger.info("Attempting to initialize ccxt.mexc client...")
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': secret,
            'options': {
                'recvWindow': 10000  # Increased window for more tolerance
            },
            'adjustForTimeDifference': True, # Enable automatic time synchronization
        })
        self.balance_cache = None
        logger.info("ccxt.mexc client object created.")
        self.balance_cache_time = 0

    async def fetch_spot_symbols(self, filter='USDT'):
        """
        Fetches spot symbols, optionally filtering by a quote currency.
        """
        if not self.exchange:
            return []
        try:
            markets = await self.exchange.load_markets()
            symbols = [
                s for s in markets
                if markets[s]['spot']
                and (not filter or markets[s]['quote'] == filter)
            ]
            return symbols
        except ccxt.ExchangeError as e:
            logger.error(f"Error fetching symbols: {e}", exc_info=True)
            return []

    async def place_order(self, symbol, side, type, amount, price=None):
        """
        Places an order.
        """
        if not self.exchange:
            return None
        try:
            return await self.exchange.create_order(symbol, type, side, amount, price)
        except ccxt.ExchangeError as e:
            logger.error(f"Error placing order: {e}", exc_info=True)
            return None

    async def fetch_balances(self):
        """
        Fetches the account balance, with caching.
        """
        cache_duration = 10  # seconds
        current_time = time.time()

        if self.balance_cache and (current_time - self.balance_cache_time) < cache_duration:
            return self.balance_cache

        if not self.exchange:
            return {}
        try:
            logger.info("Attempting to fetch balances from MEXC...")
            self.balance_cache = await self.exchange.fetch_balance()
            self.balance_cache_time = current_time
            logger.info("Successfully fetched balances from MEXC.")
            return self.balance_cache
        except ccxt.ExchangeError as e:
            logger.error(f"Error fetching balance from MEXC: {e}", exc_info=True)
            return {}

    async def get_available_balance(self, asset='USDT'):
        """
        Gets the available balance for a specific asset.
        """
        balances = await self.fetch_balances()
        return balances.get(asset, {}).get('free', 0)

    async def get_balance(self, asset='USDT'):
        """
        Gets the total balance for a specific asset.
        """
        balances = await self.fetch_balances()
        return balances.get(asset, {}).get('total', 0)
