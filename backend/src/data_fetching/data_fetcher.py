import yfinance as yf
import pandas as pd

def get_tsx_composite_symbols():
    """
    Fetches the list of S&P/TSX Composite Index stock symbols from Wikipedia.
    Returns a list of symbols with '.TO' appended if not already present.
    """
    url = "https://en.wikipedia.org/wiki/S%26P/TSX_Composite_Index"
    tables = pd.read_html(url)
    df = tables[0]  # Assuming the first table contains the stock symbols
    symbols = df["Symbol"].tolist()
    # Ensure symbols are in the format expected by yfinance (e.g., "TD.TO")
    symbols = [sym + ".TO" if not sym.endswith(".TO") else sym for sym in symbols]
    return symbols

class StockDataFetcher:
    def __init__(self):
        """Initializes the fetcher with a list of TSX composite symbols."""
        self.tsx_symbols = get_tsx_composite_symbols()

    def get_most_active_stocks_data(self, num_stocks=50):
        """
        Fetches the latest daily data for S&P/TSX Composite Index stocks,
        sorts them by volume, and returns the top num_stocks most active stocks.
        Returns a list of dictionaries containing stock data.
        """
        data = yf.download(self.tsx_symbols, period="1d", group_by="ticker")
        stock_data = []
        for symbol in self.tsx_symbols:
            if symbol in data:
                stock_info = data[symbol].iloc[0]
                stock_data.append({
                    "symbol": symbol,
                    "date": stock_info.name.strftime("%Y-%m-%d"),
                    "open": stock_info["Open"],
                    "high": stock_info["High"],
                    "low": stock_info["Low"],
                    "close": stock_info["Close"],
                    "volume": stock_info["Volume"]
                })
        # Sort by volume in descending order
        stock_data.sort(key=lambda x: x["volume"], reverse=True)
        return stock_data[:num_stocks]

    def get_watchlist_data(self, watchlist):
        """
        Fetches the latest daily data for the stocks in the watchlist.
        Args:
            watchlist (list): List of stock symbols (e.g., ["TD.TO", "SHOP.TO"]).
        Returns a list of dictionaries containing stock data.
        """
        return self.get_stock_data(watchlist)

    def get_stock_data(self, symbols):
        """
        Fetches the latest daily data for the given list of stock symbols.
        Args:
            symbols (list): List of stock symbols to fetch data for.
        Returns a list of dictionaries containing stock data.
        """
        data = yf.download(symbols, period="1d", group_by="ticker")
        stock_data = []
        for symbol in symbols:
            if symbol in data:
                stock_info = data[symbol].iloc[0]
                stock_data.append({
                    "symbol": symbol,
                    "date": stock_info.name.strftime("%Y-%m-%d"),
                    "open": stock_info["Open"],
                    "high": stock_info["High"],
                    "low": stock_info["Low"],
                    "close": stock_info["Close"],
                    "volume": stock_info["Volume"]
                })
        return stock_data

    def get_historical_data(self, symbol, period="60d"):
        """
        Fetches historical daily data for the given stock symbol over the specified period.
        Args:
            symbol (str): Stock symbol (e.g., "TD.TO").
            period (str): Time period for historical data (e.g., "60d" for 60 days).
        Returns a list of dictionaries containing historical stock data.
        """
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        return data.reset_index().to_dict(orient="records")
