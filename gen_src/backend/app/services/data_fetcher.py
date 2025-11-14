import logging
from typing import List, Dict, Any

import aiohttp

# The project's dependency context is currently empty for `app.core.config`.
# We are assuming it provides a `settings` object with the following attributes:
# - API_BASE_URL: str (e.g., "https://financialmodelingprep.com/api")
# - API_KEY: str (Your API key for the financial data provider)
# This is a common pattern using Pydantic's BaseSettings.
from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_tsx_active_stocks() -> List[Dict[str, Any]]:
    """
    Fetches a list of the most active TSX stocks from the data provider.

    This function uses a stock screener endpoint to approximate "most active"
    by filtering for high-volume stocks on the TSX exchange.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing an
                               active stock. Returns an empty list on failure.
    """
    # Using a stock screener is a common way to find active stocks for a specific exchange
    # if a dedicated "most-active" endpoint for that exchange isn't available.
    url = f"{settings.API_BASE_URL}/v3/stock-screener"
    params = {
        "exchange": "TSX",
        "volumeMoreThan": 100000,  # Filter for stocks with significant trading volume
        "limit": 50,               # As per requirement for the 50 most active stocks
        "apikey": settings.API_KEY
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
                data = await response.json()
                if isinstance(data, list):
                    return data
                else:
                    logger.warning(f"Received non-list data for active stocks: {data}")
                    return []
    except aiohttp.ClientError as e:
        logger.error(f"AIOHTTP client error fetching active TSX stocks: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching active TSX stocks: {e}")
        return []


async def fetch_historical_daily_data(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetches historical daily data for a given stock symbol on the TSX.

    Args:
        symbol (str): The stock symbol (e.g., "RY" for Royal Bank). The function
                      will append the necessary exchange suffix.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a day's
                               historical data. Returns an empty list on failure.
    """
    # Financial data APIs often use a suffix for non-US exchanges, e.g., ".TO" for TSX.
    tsx_symbol = f"{symbol.upper()}.TO"
    url = f"{settings.API_BASE_URL}/v3/historical-price-full/{tsx_symbol}"
    params = {"apikey": settings.API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                # The historical data is often nested under a 'historical' key
                return data.get("historical", [])
    except aiohttp.ClientError as e:
        logger.error(f"AIOHTTP client error fetching historical data for {symbol}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching historical data for {symbol}: {e}")
        return []


async def fetch_realtime_quote(symbol: str) -> Dict[str, Any]:
    """
    Fetches the latest real-time price quote for a single stock symbol on the TSX.

    Args:
        symbol (str): The stock symbol (e.g., "BCE" for Bell Canada).

    Returns:
        Dict[str, Any]: A dictionary containing the real-time quote data.
                        Returns an empty dictionary on failure or if not found.
    """
    tsx_symbol = f"{symbol.upper()}.TO"
    url = f"{settings.API_BASE_URL}/v3/quote/{tsx_symbol}"
    params = {"apikey": settings.API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                # Quote APIs often return a list, even for a single symbol query.
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                else:
                    logger.warning(f"No real-time quote data found for symbol {symbol}. API response: {data}")
                    return {}
    except aiohttp.ClientError as e:
        logger.error(f"AIOHTTP client error fetching real-time quote for {symbol}: {e}")
        return {}
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching real-time quote for {symbol}: {e}")
        return {}
