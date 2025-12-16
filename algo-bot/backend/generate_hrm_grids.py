# generate_hrm_grids.py
import sqlite3
import pandas as pd
import numpy as np
import random
import logging
import os
from config import DB_FILE
from db import create_tables

RELIABLE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "LTCUSDT", "BCHUSDT", 
                    "ETCUSDT", "DOGEUSDT", "TRXUSDT", "BNBUSDT", "ATOMUSDT"]
SAMPLES_PER_SYMBOL = 100
WINDOW = 40  # Reduced
GRID_H, GRID_W = 40, 40  # 40x40
CANDLE_ROWS = 28  # Top 70%
VOL_ROWS = 12     # Bottom 30%
OUTPUT_DIR = "hrm_40x40_1000k"  # New dir
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log_norm(series):
    series = series + 1e-8
    log_s = np.log(series)
    return (log_s - log_s.min()) / (log_s.max() - log_s.min() + 1e-8)

def render_grid(df_slice):
    grid = np.zeros((GRID_H, GRID_W), dtype=int)
    
    if len(df_slice) < WINDOW: 
        return grid
    
    prices = df_slice[['open', 'high', 'low', 'close']].values[-WINDOW:]
    vols = df_slice['volume'].values[-WINDOW:]
    
    # Normalize prices (high/low for scale) and volume separately
    price_vals = np.concatenate([prices[:,1], prices[:,2]])  # Highs/lows
    price_norm = log_norm(price_vals)
    vol_norm = log_norm(vols)
    
    for col in range(WINDOW):
        o, h, l, c = prices[col]
        # Individual norm per candle (preserves relative height)
        candle_vals = np.array([o, h, l, c])
        candle_norm = log_norm(candle_vals)
        o_n, h_n, l_n, c_n = candle_norm
        
        high_r = int(h_n * (CANDLE_ROWS - 1))
        low_r = int(l_n * (CANDLE_ROWS - 1))
        open_r = int(o_n * (CANDLE_ROWS - 1))
        close_r = int(c_n * (CANDLE_ROWS - 1))
        
        color = 3 if c >= o else 6
        grid[min(open_r, close_r):max(open_r, close_r)+1, col] = color
        grid[low_r:high_r+1, col] = 1  # Wick
        
        vol_h = int(vol_norm[col] * (VOL_ROWS - 1))
        grid[CANDLE_ROWS : CANDLE_ROWS + vol_h + 1, col] = min(9, vol_h // 2 + 1)
    
    return grid

def generate_100_samples():
    conn = sqlite3.connect(DB_FILE)
    all_grids = []
    all_labels = []
    
    for sym in RELIABLE_SYMBOLS:
        # Prioritize 1h for detail + variety
        df = pd.read_sql("""
            SELECT timestamp, open, high, low, close, volume FROM long_term_klines
            WHERE symbol=? AND interval='1h' ORDER BY timestamp
        """, conn, params=(sym,))
        # Need 1 extra candle for the label
        if len(df) < WINDOW + 501: 
            logging.warning(f"Skipping {sym}: insufficient 1h data")
            continue
        
        df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].apply(pd.to_numeric)
        
        sym_grids = []
        sym_labels = []
        vol_roll = df['volume'].rolling(200).mean()
        
        for _ in range(SAMPLES_PER_SYMBOL):
            # Ensure we have room for the window and the next candle for the label
            max_start_index = len(df) - WINDOW - 1

            if random.random() < 0.4:  # Random sampling
                start = random.randint(0, max_start_index)
            elif random.random() < 0.7:  # High vol bias
                peak = vol_roll.idxmax()
                start = max(0, peak - WINDOW // 2 + random.randint(-100, 100))
            else:  # Trend extreme (local max/min close)
                extremes = df['close'].rolling(100).apply(lambda x: x.idxmax() if x.iloc[-1] == x.max() else (x.idxmin() if x.iloc[-1] == x.min() else np.nan))
                valid = extremes.dropna()
                if not valid.empty:
                    peak = random.choice(valid.values) # .values is important here
                    start = max(0, int(peak) - WINDOW // 2 + random.randint(-50, 50))
                else:
                    start = random.randint(0, max_start_index)
            
            start = max(0, min(start, max_start_index))
            slice_df = df.iloc[start:start + WINDOW]
            grid = render_grid(slice_df)
            sym_grids.append(grid)

            # Generate the label: 1 if the next candle's close is higher, 0 otherwise
            next_candle_close = df.iloc[start + WINDOW]['close']
            last_candle_in_window_close = slice_df.iloc[-1]['close']
            label = 1 if next_candle_close > last_candle_in_window_close else 0
            sym_labels.append(label)
        
        np.save(f"{OUTPUT_DIR}/{sym}_100_grids.npy", np.array(sym_grids))
        np.save(f"{OUTPUT_DIR}/{sym}_100_labels.npy", np.array(sym_labels))
        all_grids.extend(sym_grids)
        all_labels.extend(sym_labels)
    
    np.save(f"{OUTPUT_DIR}/all_grids.npy", np.array(all_grids))
    np.save(f"{OUTPUT_DIR}/all_labels.npy", np.array(all_labels))
    logging.info(f"Generated 1000 varied 40x40 HRM grids (100/symbol)")

if __name__ == "__main__":
    create_tables()  # Ensure the long_term_klines table exists
    generate_100_samples()