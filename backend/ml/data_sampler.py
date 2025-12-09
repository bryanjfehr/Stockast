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
from ml.rgb_processor import convert_to_rgb
from ml.data_fetcher import fetch_multi_histories, get_top_symbols, fetch_one_history

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HRM Grid Constants ---
T, S, H, A = 84, 8, 3, 10

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

def generate_puzzle_samples(histories: Dict[str, pd.DataFrame], output_dir: str, seq_len=84, num_samples=5000, vocab_size=256):
    """
    Generates tokenized "puzzle" samples suitable for the pretrain.py script.
    This involves quantizing continuous data into a discrete vocabulary.

    Args:
        histories (Dict[str, pd.DataFrame]): Dictionary of {symbol: DataFrame}.
        output_dir (str): Directory to save the tokenized data files.
        seq_len (int): The sequence length for each puzzle.
        num_samples (int): The total number of samples to generate.
        vocab_size (int): The number of discrete bins for quantization.
    """
    logging.info(f"Starting puzzle sample generation for pre-training...")
    os.makedirs(output_dir, exist_ok=True)

    all_series_data = []
    for symbol, df in histories.items():
        try:
            rgb_df = convert_to_rgb(df)
            if rgb_df is None or len(rgb_df) < seq_len:
                continue
            # We only need the 'R', 'G', 'B' channels for this example
            series = rgb_df[['R', 'G', 'B']].values
            all_series_data.append(series)
        except Exception:
            logging.warning(f"Could not process {symbol} for puzzle generation.", exc_info=True)

    if not all_series_data:
        logging.error("No valid RGB series data could be generated. Aborting.")
        return

    # Create windows from all available data
    all_windows = []
    for series in all_series_data:
        num_possible_starts = len(series) - seq_len + 1
        for i in range(num_possible_starts):
            all_windows.append(series[i:i+seq_len])

    if len(all_windows) < num_samples:
        logging.warning(f"Only able to generate {len(all_windows)} samples, requested {num_samples}.")
        num_samples = len(all_windows)

    # Randomly select final samples and save them as individual tokenized files
    selected_indices = np.random.choice(len(all_windows), num_samples, replace=False)
    for i, idx in enumerate(selected_indices):
        window = all_windows[idx]
        # Quantize float values (0-255) into discrete integer tokens (0-vocab_size-1)
        tokens = (window / 256.0 * vocab_size).astype(np.int32)
        # Save as a flat sequence of tokens, which PuzzleDataset can read
        tokens.tofile(os.path.join(output_dir, f"puzzle_{i}.bin"))

    logging.info(f"Successfully generated and saved {num_samples} tokenized puzzle files to '{output_dir}'.")


if __name__ == "__main__":
    # This block is for demonstration and testing of the data_sampler module.
    # The primary entry point for building the dataset and training the model
    # is now located in `scripts/build_and_train.py`.
    logging.info("Running data_sampler.py as a standalone script for demonstration.")
    logging.info("This will not train the model. To build the dataset and train, run:")
    logging.info("python scripts/build_and_train.py")

    # You can add simple test logic here if needed, for example:
    # exchange = ccxt.mexc()
    # symbols = get_top_symbols(exchange, 5)
    # histories = fetch_multi_histories(symbols, days_back=30)
    # if histories:
    #     generate_samples(histories, seq_len=60, num_per_sym=5, output_file="test_samples.pt")