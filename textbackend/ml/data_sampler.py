import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

import ccxt
import numpy as np
import pandas as pd
import torch
from numpy.polynomial.legendre import Legendre

# Assuming rgb_processor is in ../utils/
from utils.rgb_processor import convert_to_rgb
from utils.data_fetcher import fetch_multi_histories

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

def build_4d_from_histories(histories: Dict[str, pd.DataFrame], lookback=60, horizon=24, hierarchy=3) -> np.ndarray:
    """
    Builds a 4D tensor (T, S, H, A) from a dictionary of historical data.

    Args:
        histories: Dictionary of {symbol: DataFrame}.
        lookback: The historical window size (part of T).
        horizon: The future window to predict (part of T).
        hierarchy: The number of hierarchical levels (H).

    Returns:
        A 4D numpy array with shape (T, S, H, A) and future values masked with NaN.
    """
    T = lookback + horizon
    S = len(histories)
    A = 10  # Example value, adjust as needed
    
    # Get the list of symbols
    symbols = list(histories.keys())
    
    # Find the common start date for all histories
    common_start = max([df.index.min() for df in histories.values()])
    
    # Trim histories to the common start date
    trimmed_histories = {sym: df[df.index >= common_start] for sym, df in histories.items()}
    
    # Find the minimum length among all trimmed histories
    min_len = min([len(df) for df in trimmed_histories.values()])
    
    if min_len < T:
        raise ValueError(f"All histories must have at least T={T} data points after aligning start dates.")

    # Initialize the 4D tensor
    tensor = np.full((T, S, hierarchy, A), np.nan, dtype=np.float32)

    for s_idx, symbol in enumerate(symbols):
        df = trimmed_histories[symbol].iloc[:T]

        # Normalize data relativistically (0-1 % changes)
        price_norm = (df['close'] - df['close'].min()) / (df['close'].max() - df['close'].min())
        volume_norm = (df['volume'] - df['volume'].min()) / (df['volume'].max() - df['volume'].min())
        
        # Assuming RGB signals are pre-calculated and present in the DataFrame
        # S=0-3: OHLC, S=4-7: RGB signals
        tensor[:lookback, s_idx, 0, 0] = (df['open'][:lookback].pct_change() + 1).fillna(1)
        tensor[:lookback, s_idx, 0, 1] = (df['high'][:lookback].pct_change() + 1).fillna(1)
        tensor[:lookback, s_idx, 0, 2] = (df['low'][:lookback].pct_change() + 1).fillna(1)
        tensor[:lookback, s_idx, 0, 3] = (df['close'][:lookback].pct_change() + 1).fillna(1)
        
        # RGB-derived signals in S=4-7
        if all(col in df.columns for col in ['R', 'G', 'B']):
            tensor[:lookback, s_idx, 1, 0] = df['R'][:lookback].values / 255.0
            tensor[:lookback, s_idx, 1, 1] = df['G'][:lookback].values / 255.0
            tensor[:lookback, s_idx, 1, 2] = df['B'][:lookback].values / 255.0
        
        # Mask future T slots (horizon) as NaN - already initialized with NaN

    return tensor


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

def flatten_to_matrix_sequence(grid: torch.Tensor, mode='row_major') -> torch.Tensor:
    """
    Flattens a 2D grid into a 1D sequence.

    Args:
        grid (torch.Tensor): The 2D input tensor.
        mode (str): The flattening mode ('row_major', 'column_major').

    Returns:
        torch.Tensor: The flattened 1D tensor.
    """
    if grid.dim() != 2:
        raise ValueError(f"Input grid must be 2D, but got {grid.dim()} dimensions.")
    
    if mode == 'row_major':
        return grid.flatten()
    elif mode == 'column_major':
        return grid.t().flatten()
    else:
        raise ValueError(f"Unsupported mode: {mode}. Use 'row_major' or 'column_major'.")

def flatten_to_polynomial_sequence(grid: torch.Tensor, degree=3) -> torch.Tensor:
    """
    Flattens a 2D grid to a 1D sequence of Legendre polynomial coefficients.
    Each row of the grid is treated as a signal slice.

    Args:
        grid (torch.Tensor): The 2D input tensor.
        degree (int): The degree of the Legendre polynomial to fit.

    Returns:
        torch.Tensor: The flattened 1D tensor of coefficients.
    """
    if grid.dim() != 2:
        raise ValueError(f"Input grid must be 2D, but got {grid.dim()} dimensions.")

    grid_np = grid.numpy()
    all_coeffs = []

    # Create the x-axis for fitting, normalized to [-1, 1] for Legendre polynomials
    x = np.linspace(-1, 1, grid.shape[1])

    for row_signal in grid_np:
        # Fit a Legendre polynomial of the specified degree
        poly = Legendre.fit(x, row_signal, deg=degree)
        
        # Get the coefficients and append to our list
        # .convert().coef gives coefficients in standard power basis, which is fine
        coeffs = poly.convert().coef
        all_coeffs.extend(coeffs)

    return torch.tensor(all_coeffs, dtype=torch.float32)

def generate_samples(histories: Dict[str, pd.DataFrame], seq_len=60, num_per_sym=20, output_file="rgb_samples.pt") -> None:
    """
    Generates windowed samples from RGB-processed histories and saves them to a file.

    Args:
        histories (Dict[str, pd.DataFrame]): Dictionary of {symbol: DataFrame}.
        seq_len (int): The sequence length for each sample.
        num_per_sym (int): The number of random samples to generate per symbol.
        output_file (str): The path to save the output tensor.
    """
    all_samples = []
    
    logging.info("Starting sample generation...")

    for symbol, df in histories.items():
        # It's assumed fetch_multi_histories already provides the base data.
        # We process it to get RGB values.
        try:
            rgb_df = convert_to_rgb(df)
            if rgb_df is None or rgb_df.empty:
                logging.warning(f"Could not convert {symbol} to RGB, skipping.")
                continue
        except Exception as e:
            logging.error(f"Error converting {symbol} to RGB: {e}", exc_info=True)
            continue

        # We need 'R', 'G', 'B', and 'embed_4' (the line value)
        required_cols = ['R', 'G', 'B', 'embed_4']
        if not all(col in rgb_df.columns for col in required_cols):
            logging.warning(f"DataFrame for {symbol} is missing required RGB columns after conversion, skipping.")
            continue
            
        if len(rgb_df) < seq_len:
            logging.info(f"Skipping {symbol} due to insufficient data points ({len(rgb_df)}) for seq_len {seq_len}.")
            continue

        sample_data = rgb_df[required_cols].values
        
        num_possible_starts = len(sample_data) - seq_len + 1
        
        # Choose random start indices for diversity
        replace = num_possible_starts < num_per_sym
        start_indices = np.random.choice(num_possible_starts, num_per_sym, replace=replace)

        for start in start_indices:
            window = sample_data[start : start + seq_len]
            all_samples.append(window)
            
    if not all_samples:
        logging.error("No samples were generated. Check data fetching and processing steps.")
        return

    # Convert to a single tensor
    tensor = torch.tensor(np.array(all_samples), dtype=torch.float32)
    
    # Save the tensor
    torch.save(tensor, output_file)
    logging.info(f"Saved tensor with shape {tensor.shape} to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="rgb_samples.pt", help="Output tensor file")
    parser.add_argument("--num_samples_per_sym", type=int, default=20, help="Samples per symbol")
    parser.add_argument("--seq_len", type=int, default=60, help="Sequence length of each sample")
    parser.add_argument("--days_back", type=int, default=365, help="Days of history to fetch")
    parser.add_argument("--api_key", help="MEXC API key (optional for public)")
    parser.add_argument("--secret", help="MEXC secret")
    args = parser.parse_args()
    
    exchange = ccxt.mexc({'apiKey': args.api_key, 'secret': args.secret, 'enableRateLimit': True})
    
    # 1. Fetch top symbols
    symbols = get_top_symbols(exchange, 50)
    if not symbols:
        logging.error("Could not retrieve top symbols. Exiting.")
    else:
        logging.info(f"Found {len(symbols)} symbols to process.")
    
        # 2. Fetch histories for these symbols
        histories = fetch_multi_histories(symbols, exchange, days_back=args.days_back)
    
        if not histories:
            logging.error("Failed to fetch any historical data. Exiting.")
        else:
            # 3. Generate and save samples
            generate_samples(
                histories, 
                seq_len=args.seq_len, 
                num_per_sym=args.num_samples_per_sym,
                output_file=args.output
            )