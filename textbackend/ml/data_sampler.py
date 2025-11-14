import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import ccxt
import numpy as np
import pandas as pd
import torch

# Assuming rgb_processor is in ../utils/
from utils.rgb_processor import convert_to_rgb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HRM Grid Constants ---
T, S, H, A = 84, 8, 3, 10

def get_top_symbols(exchange: ccxt.Exchange, limit: int = 50) -> List[str]:
    """Fetch top spot symbols by quote volume (USDT pairs for diversity)."""
    try:
        markets = exchange.load_markets()
        usdt_pairs = {s for s in markets if s.endswith('/USDT') and markets[s].get('spot', False)}
        tickers = exchange.fetch_tickers()
        
        # Filter tickers that are USDT spot pairs and have quoteVolume
        valid_tickers = [
            (symbol, ticker['quoteVolume'])
            for symbol, ticker in tickers.items()
            if symbol in usdt_pairs and ticker.get('quoteVolume') is not None
        ]
        
        sorted_pairs = sorted(valid_tickers, key=lambda x: x[1], reverse=True)
        
        if not sorted_pairs:
            logging.warning("Could not fetch tickers or find any with quoteVolume. Falling back to market list.")
            return list(usdt_pairs)[:limit]
            
        return [p[0] for p in sorted_pairs[:limit]]
    except Exception as e:
        logging.error(f"Failed to get top symbols: {e}", exc_info=True)
        return []

def fetch_one_history(sym: str, exchange: ccxt.Exchange, days_back: int = 365) -> Optional[pd.DataFrame]:
    """Fetch 1y 1h OHLCV for symbol."""
    since = int((pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days_back)).timestamp() * 1000)
    try:
        ohlcv = exchange.fetch_ohlcv(sym, '1h', since=since, limit=1000)
        if not ohlcv:
            logging.warning(f"No OHLCV data returned for {sym}.")
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.dropna(inplace=True)
        if len(df) < T * 2:  # Ensure enough data for processing and windowing
            logging.info(f"Skipping {sym} due to insufficient data points ({len(df)}).")
            return None
        return df
    except Exception as e:
        logging.error(f"Failed to fetch history for {sym}: {e}")
        return None

def build_hrm_grids(rgb_histories: List[pd.DataFrame]) -> List[np.ndarray]:
    """
    Builds 4D HRM grids from a list of RGB-processed histories.
    A grid is formed by taking T=84 steps from S=8 symbols.
    """
    grids = []
    num_histories = len(rgb_histories)
    if num_histories < S:
        logging.warning(f"Not enough histories ({num_histories}) to form a full grid of {S} symbols.")
        return []

    # Find the minimum length to ensure all symbols in a grid have enough data
    min_len = min(len(h) for h in rgb_histories)
    if min_len < T:
        logging.warning(f"Histories are too short ({min_len}) to create grids of length {T}.")
        return []

    # Create overlapping grids
    for i in range(0, num_histories - S + 1, S // 2): # Overlap by 50%
        for t_start in range(0, min_len - T + 1, T // 4): # Overlap by 75%
            grid = np.zeros((T, S, H, A), dtype=np.float32)
            symbol_slice = rgb_histories[i : i + S]

            for s_idx, history in enumerate(symbol_slice):
                # Take T steps for the current symbol
                time_slice = history.iloc[t_start : t_start + T]
                
                # Map the 4 channels (R,G,B,embed_4) into the (H, A) dimensions
                # This is a simple mapping; a more complex one could be used.
                # H=0: RGB, H=1: EMA, H=2: spare
                grid[:, s_idx, 0, 0] = time_slice['R'].values
                grid[:, s_idx, 0, 1] = time_slice['G'].values
                grid[:, s_idx, 0, 2] = time_slice['B'].values
                grid[:, s_idx, 1, 0] = time_slice['embed_4'].values
            
            grids.append(grid)
    
    logging.info(f"Built {len(grids)} HRM grids.")
    return grids

def generate_training_samples(grids: List[np.ndarray], num_samples: int, seq_len: int = 60) -> torch.Tensor:
    """
    Flattens HRM grids and samples diverse windows for training.
    Each sample is a window of shape (seq_len, S * H * A).
    """
    samples = []
    if not grids:
        return torch.empty(0)

    # Flatten each grid from (T, S, H, A) to (T, S*H*A)
    flattened_grids = [grid.reshape(T, -1) for grid in grids]

    # Calculate how many samples to draw from each grid to ensure diversity
    num_per_grid = max(1, num_samples // len(flattened_grids))

    for flat_grid in flattened_grids:
        if len(flat_grid) < seq_len:
            continue # Should not happen if checks are done before
        
        # Randomly select starting points for windows
        num_possible_starts = len(flat_grid) - seq_len + 1
        replace = num_possible_starts < num_per_grid
        start_indices = np.random.choice(num_possible_starts, num_per_grid, replace=replace)

        for start in start_indices:
            samples.append(flat_grid[start : start + seq_len])
            if len(samples) >= num_samples:
                break
        if len(samples) >= num_samples:
            break

    return torch.tensor(np.array(samples), dtype=torch.float32)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="rgb_samples.pt", help="Output tensor file")
    parser.add_argument("--num_samples", type=int, default=1000, help="Target samples")
    parser.add_argument("--seq_len", type=int, default=60, help="Sequence length of each sample")
    parser.add_argument("--api_key", help="MEXC API key (optional for public)")
    parser.add_argument("--secret", help="MEXC secret")
    args = parser.parse_args()
    
    exchange = ccxt.mexc({'apiKey': args.api_key, 'secret': args.secret, 'enableRateLimit': True})
    symbols = get_top_symbols(exchange, 50)
    logging.info(f"Found {len(symbols)} symbols to process.")
    
    processed_histories = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_one_history, s, exchange): s for s in symbols}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                history_df = future.result()
                if history_df is not None:
                    rgb_df = convert_to_rgb(history_df)
                    if rgb_df is not None:
                        processed_histories.append(rgb_df)
                        logging.info(f"Successfully processed {symbol}")
            except Exception as exc:
                logging.error(f'{symbol} generated an exception: {exc}')

    if processed_histories:
        hrm_grids = build_hrm_grids(processed_histories)
        if hrm_grids:
            tensor = generate_training_samples(hrm_grids, args.num_samples, args.seq_len)
            torch.save(tensor, args.output)
            logging.info(f"Saved tensor with shape {tensor.shape} to {args.output}")
        else:
            logging.error("Could not build any HRM grids from the processed data.")
    else:
        logging.error("No historical data could be processed.")