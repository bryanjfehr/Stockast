import logging
import os
import sys
import subprocess
import numpy as np
from dotenv import load_dotenv
import ccxt

# Add the backend root to the Python path to allow for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.data_fetcher import get_top_symbols, fetch_multi_histories
from ml.data_sampler import generate_puzzle_samples
from ml.rgb_processor import convert_to_rgb

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Main function to orchestrate the data fetching, sampling, and model training process.
    """
    # --- Load Environment Variables ---
    # This will load the .env file in the current directory (backend/)
    load_dotenv()
    mexc_api_key = os.getenv("MEXC_API_KEY")
    mexc_secret = os.getenv("MEXC_SECRET")

    if not mexc_api_key or not mexc_secret:
        logging.error("MEXC_API_KEY and MEXC_SECRET must be set in your .env file. Aborting.")
        return

    # --- Configuration ---
    dataset_path = 'puzzle_dataset' # Directory for tokenized samples
    model_path = 'hrm_intra.pth'
    num_symbols_to_fetch = 64 # Should be a multiple of S (8) for clean grid creation

    # --- Step 1: Fetch Data ---
    logging.info("Initializing authenticated exchange client to fetch top symbols...")
    try:
        exchange = ccxt.mexc({
            'apiKey': mexc_api_key,
            'secret': mexc_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} # Explicitly use spot markets
        })
        symbols_to_fetch = get_top_symbols(exchange, limit=num_symbols_to_fetch)
        if not symbols_to_fetch:
            raise RuntimeError("Could not fetch top symbols. Aborting.")
        logging.info(f"Identified {len(symbols_to_fetch)} symbols for data collection.")
    except Exception as e:
        logging.error(f"Failed to initialize exchange or get symbols: {e}", exc_info=True)
        return

    histories = fetch_multi_histories(exchange, symbols_to_fetch, timeframe='1h', days_back=365)
    if not histories:
        logging.error("No historical data was fetched. Cannot proceed with dataset generation.")
        return

    # --- Step 2: Generate Tokenized Puzzle Dataset ---
    # The pretrain.py script expects data in a specific format.
    # We will now generate tokenized files that its PuzzleDataset can read.
    logging.info(f"Generating tokenized puzzle samples and saving to '{dataset_path}' directory...")
    generate_puzzle_samples(histories, output_dir=dataset_path, num_samples=5000, seq_len=84, vocab_size=256)
    logging.info("Dataset generation complete.")

    # --- Step 3: Run the Advanced Pre-training Script ---
    logging.info("Initiating model training using ml/HRM/pretrain.py...")
    pretrain_script_path = os.path.join('ml', 'HRM', 'pretrain.py')

    # We will execute pretrain.py as a subprocess, passing configuration via command line.
    # This is how Hydra-based applications are typically run.
    command = [
        sys.executable, pretrain_script_path,
        f"data_path={dataset_path}",
        "arch=mamba/s", # Example architecture, adjust as needed from your configs
        "epochs=10",
        "global_batch_size=32"
    ]

    subprocess.run(command, check=True)

    logging.info("Training complete. The application is ready to be started.")

if __name__ == "__main__":
    main()