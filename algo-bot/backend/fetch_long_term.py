# fetch_long_term.py
import logging
from datetime import datetime
from db import create_tables, save_long_term_klines
from backtest import get_historical_data  # Reuse your robust fetcher

logging.basicConfig(level=logging.INFO)

RELIABLE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "LTCUSDT", "BCHUSDT", 
                    "ETCUSDT", "DOGEUSDT", "TRXUSDT", "BNBUSDT", "ATOMUSDT"]
INTERVALS = ['1d', '1h', '4h']  # Proven data
END_DATE = datetime.now().strftime("%Y-%m-%d")

if __name__ == "__main__":
    # Ensure all database tables, including long_term_klines, exist.
    create_tables()

    for sym in RELIABLE_SYMBOLS:
        for intv in INTERVALS:
            start = "2018-01-01" if intv == '1d' else "2023-01-01"
            logging.info(f"Fetching {intv} for {sym} from {start}...")
            klines = get_historical_data(sym, start, END_DATE, intv)
            
            if klines:
                # Save the fetched data to the dedicated long-term table
                save_long_term_klines(sym, intv, klines)
                logging.info(f"Success: Processed {len(klines)} {intv} klines for {sym}")
            else:
                logging.warning(f"No data fetched for {sym} {intv}")