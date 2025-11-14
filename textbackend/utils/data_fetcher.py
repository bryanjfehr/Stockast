import time
import logging
from typing import List
from ..api.mexc import MEXCWrapper
from ..db.utils import get_db_session
from ..db.models import OHLCV, Symbol
from ..config import RATE_LIMIT_BACKOFF_FACTOR

logging.basicConfig(level=logging.INFO)

class DataFetcher:
    def __init__(self, mexc_wrapper: MEXCWrapper):
        self.mexc = mexc_wrapper

    def fetch_and_store_symbols(self):
        """Fetches and stores all spot symbols."""
        with get_db_session() as session:
            symbols = self.mexc.get_spot_symbols()
            for symbol_name in symbols:
                if not session.query(Symbol).filter_by(name=symbol_name).first():
                    session.add(Symbol(name=symbol_name))

    def fetch_and_store_ohlcv(self, symbols: List[str], timeframe: str):
        """Fetches and stores OHLCV data for a list of symbols."""
        with get_db_session() as session:
            for symbol_name in symbols:
                try:
                    symbol_obj = session.query(Symbol).filter_by(name=symbol_name).first()
                    if not symbol_obj:
                        logging.warning(f"Symbol {symbol_name} not found in database.")
                        continue

                    ohlcv_data = self.mexc.fetch_ohlcv(symbol_name, timeframe)
                    for d in ohlcv_data:
                        ohlcv = OHLCV(
                            symbol_id=symbol_obj.id,
                            timestamp=d[0],
                            open=d[1],
                            high=d[2],
                            low=d[3],
                            close=d[4],
                            volume=d[5]
                        )
                        session.add(ohlcv)
                    time.sleep(self.mexc.exchange.rateLimit / 1000 * RATE_LIMIT_BACKOFF_FACTOR)
                except Exception as e:
                    logging.error(f"Error fetching OHLCV for {symbol_name}: {e}")
