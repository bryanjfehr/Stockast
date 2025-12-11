# api.py
import requests
import time
import threading
import logging
from typing import List, Dict, Any, Union
from config import MEXC_API_BASE, MEXC_API_KEY

logger = logging.getLogger(__name__)

class MexcAPI:
    """
    Wrapper for MEXC public API endpoints.
    Handles basic rate limiting and error checking.
    """
    def __init__(self):
        if not MEXC_API_KEY:
            # The bot cannot function without an API key.
            # This provides a clear, immediate error instead of failing on every API call.
            raise ValueError("MEXC_API_KEY is not set. Please check your .env file and ensure it's correctly configured.")

        self.session = requests.Session()
        self.session.headers.update({
            # The API Key is not required for public endpoints.
            # 'X-MEXC-APIKEY': MEXC_API_KEY,
            'Accept': 'application/json',
            'User-Agent': 'Stockast-Algo-Bot/1.0'
        })
        self.base_url = MEXC_API_BASE
        self.rate_limit_delay = 0.1  # Seconds between calls (adjust for weights)
        self._rate_limit_lock = threading.Lock()
        self._last_request_time = 0

    def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Generic GET request with rate limit delay and error handling.
        Ensures rate limit is respected across all threads.
        """
        with self._rate_limit_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
            self._last_request_time = time.time()
        
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Requesting URL: {url} with params: {params or {}}")
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # Handle API errors that return 200 OK but have an error message in the body
            if isinstance(data, dict) and 'code' in data and data['code'] != 200:
                logger.error(f"API error for {url}: {data.get('msg', 'Unknown')}")
                raise ValueError(f"API error: {data.get('msg', 'Unknown')}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise ValueError(f"Request failed: {e}")

    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Fetch exchange info (symbols, filters). Weight: 10
        """
        return self._request('/api/v3/exchangeInfo')

    def get_klines(self, symbol: str, interval: str = '60m', limit: int = 100, startTime: int = None, endTime: int = None) -> List[List[str]]:
        """
        Fetch kline data for a symbol. Weight: 1
        Supports historical ranges via startTime/endTime (ms Unix timestamps).
        Returns: [[open_time, open, high, low, close, volume, close_time, quote_volume], ...]
        """
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        if startTime is not None:
            params['startTime'] = startTime
        if endTime is not None:
            params['endTime'] = endTime
        data = self._request('/api/v3/klines', params)
        return data

    def get_ticker_24hr(self, symbol: str = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Fetch 24hr stats for one or all symbols. Weight: 1 (single) or 40 (all)
        """
        params = {'symbol': symbol} if symbol else {}
        return self._request('/api/v3/ticker/24hr', params)

    def get_price(self, symbol: str) -> Dict[str, str]:
        """
        Fetch current price. Weight: 1
        """
        params = {'symbol': symbol}
        data = self._request('/api/v3/ticker/price', params)
        return data

    def get_depth(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Fetch order book depth. Weight: 1
        """
        params = {'symbol': symbol, 'limit': limit}
        return self._request('/api/v3/depth', params)

# Global instance for easy import
api = MexcAPI()