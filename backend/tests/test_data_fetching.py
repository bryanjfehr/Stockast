import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd
import aiohttp
from data_fetching.api_clients import PolygonClient
from data_fetching.data_fetcher import StockDataFetcher, get_tsx_composite_symbols

# Tests for PolygonClient
@pytest.mark.asyncio
async def test_polygon_get_most_active_stocks():
    with patch('aiohttp.ClientSession.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "tickers": [
                {"ticker": "XYZ.TO", "name": "XYZ Corp", "day": {"v": 1000000}, "lastTrade": {"p": 50.0}},
                {"ticker": "ABC.TO", "name": "ABC Inc", "day": {"v": 500000}, "lastTrade": {"p": 30.0}},
            ]
        }
        mock_get.return_value = mock_response

        client = PolygonClient(api_key="fake_key")
        stocks = await client.get_most_active_stocks(limit=2)
        assert len(stocks) == 2
        assert stocks[0]["symbol"] == "XYZ.TO"
        assert stocks[0]["volume"] == 1000000
        assert stocks[1]["symbol"] == "ABC.TO"
        assert stocks[1]["price"] == 30.0

@pytest.mark.asyncio
async def test_polygon_get_historical_data():
    with patch('aiohttp.ClientSession.get', new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "results": [
                {"t": 1234567890, "o": 100.0, "h": 105.0, "l": 99.0, "c": 102.0, "v": 100000},
            ]
        }
        mock_get.return_value = mock_response

        client = PolygonClient(api_key="fake_key")
        data = await client.get_historical_data("XYZ.TO", "2023-01-01", "2023-01-02", "day")
        assert len(data) == 1
        assert data[0]["open"] == 100.0
        assert data[0]["close"] == 102.0
        assert data[0]["volume"] == 100000

@pytest.mark.asyncio
async def test_polygon_real_time_updates():
    with patch('aiohttp.ClientSession.ws_connect', new_callable=AsyncMock) as mock_ws_connect:
        mock_ws = AsyncMock()
        mock_ws.send_str = AsyncMock()
        mock_msg = aiohttp.WSMessage(aiohttp.WSMsgType.TEXT, '[{"ev": "T", "sym": "XYZ.TO", "t": 1234567890, "p": 50.0, "s": 100}]', '')
        mock_ws.__aiter__.return_value = [mock_msg]
        mock_ws_connect.return_value = mock_ws

        client = PolygonClient(api_key="fake_key")
        await client.subscribe_real_time("XYZ.TO")
        updates = []
        async for update in client.get_real_time_updates():
            updates.append(update)
            break  # Only fetch one update for testing
        assert len(updates) == 1
        assert updates[0]["symbol"] == "XYZ.TO"
        assert updates[0]["price"] == 50.0
        assert updates[0]["size"] == 100

# Tests for StockDataFetcher
def test_get_tsx_composite_symbols():
    with patch('pandas.read_html') as mock_read_html:
        mock_df = pd.DataFrame({"Symbol": ["ABC", "DEF.TO"]})
        mock_read_html.return_value = [mock_df]
        symbols = get_tsx_composite_symbols()
        assert symbols == ["ABC.TO", "DEF.TO"]

def test_get_most_active_stocks_data():
    with patch('yfinance.download') as mock_download:
        mock_data = pd.DataFrame({
            ("ABC.TO", "Open"): [100.0],
            ("ABC.TO", "High"): [105.0],
            ("ABC.TO", "Low"): [99.0],
            ("ABC.TO", "Close"): [102.0],
            ("ABC.TO", "Volume"): [1000000],
            ("DEF.TO", "Open"): [50.0],
            ("DEF.TO", "High"): [55.0],
            ("DEF.TO", "Low"): [49.0],
            ("DEF.TO", "Close"): [52.0],
            ("DEF.TO", "Volume"): [500000],
        }, index=[pd.Timestamp("2023-01-01")])
        mock_download.return_value = mock_data

        fetcher = StockDataFetcher()
        fetcher.tsx_symbols = ["ABC.TO", "DEF.TO"]  # Override for testing
        stocks = fetcher.get_most_active_stocks_data(num_stocks=1)
        assert len(stocks) == 1
        assert stocks[0]["symbol"] == "ABC.TO"
        assert stocks[0]["volume"] == 1000000
        assert stocks[0]["close"] == 102.0

def test_get_watchlist_data():
    with patch('yfinance.download') as mock_download:
        mock_data = pd.DataFrame({
            ("XYZ.TO", "Open"): [200.0],
            ("XYZ.TO", "High"): [205.0],
            ("XYZ.TO", "Low"): [199.0],
            ("XYZ.TO", "Close"): [202.0],
            ("XYZ.TO", "Volume"): [2000000],
        }, index=[pd.Timestamp("2023-01-01")])
        mock_download.return_value = mock_data

        fetcher = StockDataFetcher()
        watchlist = ["XYZ.TO"]
        data = fetcher.get_watchlist_data(watchlist)
        assert len(data) == 1
        assert data[0]["symbol"] == "XYZ.TO"
        assert data[0]["open"] == 200.0
        assert data[0]["volume"] == 2000000

def test_get_historical_data():
    with patch('yfinance.Ticker') as mock_ticker:
        mock_history = pd.DataFrame({
            "Open": [100.0, 102.0],
            "High": [105.0, 106.0],
            "Low": [99.0, 101.0],
            "Close": [102.0, 104.0],
            "Volume": [1000000, 1100000],
        }, index=[pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")])
        mock_ticker.return_value.history.return_value = mock_history

        fetcher = StockDataFetcher()
        data = fetcher.get_historical_data("ABC.TO", period="2d")
        assert len(data) == 2
        assert data[0]["Open"] == 100.0
        assert data[1]["Close"] == 104.0
        assert data[1]["Volume"] == 1100000
