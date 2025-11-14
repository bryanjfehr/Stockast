import logging
import ccxt
import time

logging.basicConfig(level=logging.INFO)

class MexcAPI:
    def __init__(self, api_key, secret):
        try:
            self.exchange = ccxt.mexc({
                'apiKey': api_key,
                'secret': secret,
                'options': {
                    'recvWindow': 5000
                }
            })
            self.exchange.check_required_credentials()
            self.balance_cache = None
            self.balance_cache_time = 0
        except (ccxt.AuthenticationError, ccxt.ExchangeError) as e:
            print(f"Error initializing MEXC API: {e}")
            self.exchange = None

    def fetch_spot_symbols(self, filter='USDT'):
        """
        Fetches spot symbols, optionally filtering by a quote currency.
        """
        if not self.exchange:
            return []
        try:
            markets = self.exchange.load_markets()
            symbols = [
                s for s in markets
                if markets[s]['spot']
                and (not filter or markets[s]['quote'] == filter)
            ]
            return symbols
        except ccxt.ExchangeError as e:
            print(f"Error fetching symbols: {e}")
            return []

    def place_order(self, symbol, side, type, amount, price=None):
        """
        Places an order.
        """
        if not self.exchange:
            return None
        try:
            return self.exchange.create_order(symbol, type, side, amount, price)
        except ccxt.ExchangeError as e:
            print(f"Error placing order: {e}")
            return None

    def fetch_balances(self):
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
            self.balance_cache = self.exchange.fetch_balance()
            self.balance_cache_time = current_time
            return self.balance_cache
        except ccxt.ExchangeError as e:
            print(f"Error fetching balance: {e}")
            return {}

    def get_available_balance(self, asset='USDT'):
        """
        Gets the available balance for a specific asset.
        """
        balances = self.fetch_balances()
        return balances.get(asset, {}).get('free', 0)

    def get_balance(self, asset='USDT'):
        """
        Gets the total balance for a specific asset.
        """
        balances = self.fetch_balances()
        return balances.get(asset, {}).get('total', 0)
