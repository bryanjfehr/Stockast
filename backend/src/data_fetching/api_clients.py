import aiohttp
import json
from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator

class StockAPIClient(ABC):
    @abstractmethod
    async def get_most_active_stocks(self, limit: int = 50) -> List[Dict]:
        pass

    @abstractmethod
    async def get_historical_data(self, symbol: str, start_date: str, end_date: str, interval: str) -> List[Dict]:
        pass

    @abstractmethod
    async def subscribe_real_time(self, symbol: str):
        pass

    @abstractmethod
    async def unsubscribe_real_time(self, symbol: str):
        pass

    @abstractmethod
    async def get_real_time_updates(self) -> AsyncGenerator[Dict, None]:
        pass

class PolygonClient(StockAPIClient):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.ws_url = "wss://socket.polygon.io/stocks"
        self.session = aiohttp.ClientSession()
        self.ws = None

    async def connect(self):
        if self.ws is None:
            self.ws = await self.session.ws_connect(f"{self.ws_url}?apiKey={self.api_key}")

    async def subscribe_real_time(self, symbol: str):
        await self.connect()
        await self.ws.send_str(json.dumps({"action": "subscribe", "params": f"T.{symbol}"}))

    async def unsubscribe_real_time(self, symbol: str):
        if self.ws is not None:
            await self.ws.send_str(json.dumps({"action": "unsubscribe", "params": f"T.{symbol}"}))

    async def get_real_time_updates(self) -> AsyncGenerator[Dict, None]:
        await self.connect()
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if isinstance(data, list):
                    for item in data:
                        if item["ev"] == "T":
                            yield {
                                "symbol": item["sym"],
                                "timestamp": item["t"],
                                "price": item["p"],
                                "size": item["s"]
                            }

    async def get_historical_data(self, symbol: str, start_date: str, end_date: str, interval: str) -> List[Dict]:
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/{interval}/{start_date}/{end_date}?apiKey={self.api_key}"
        async with self.session.get(url) as response:
            data = await response.json()
            if "results" in data:
                return [
                    {
                        "timestamp": candle["t"],
                        "open": candle["o"],
                        "high": candle["h"],
                        "low": candle["l"],
                        "close": candle["c"],
                        "volume": candle["v"]
                    }
                    for candle in data["results"]
                ]
            return []

    async def get_most_active_stocks(self, limit: int = 50) -> List[Dict]:
        url = f"{self.base_url}/v2/snapshot/locale/ca/markets/stocks/tickers?apiKey={self.api_key}"
        async with self.session.get(url) as response:
            data = await response.json()
            if "tickers" in data:
                tickers = data["tickers"]
                sorted_tickers = sorted(tickers, key=lambda x: x["day"]["v"], reverse=True)
                return [
                    {
                        "symbol": ticker["ticker"],
                        "name": ticker.get("name", ""),
                        "volume": ticker["day"]["v"],
                        "price": ticker["lastTrade"]["p"]
                    }
                    for ticker in sorted_tickers[:limit]
                ]
            return []

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
        await self.session.close()
