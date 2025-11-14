# data_sampler.py: Pulls 1000 diverse samples from MEXC, converts to RGB vectors
# Requirements: pip install ccxt pandas numpy torch (run locally)
# Usage: python data_sampler.py --output rgb_samples.pt --num_samples 1000
# Fetches top 50 symbols, ~20 windows per symbol for diversity (1h data, 1y back)

import argparse
import ccxt
import pandas as pd
import numpy as np
import torch
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

def get_top_symbols(exchange: ccxt.Exchange, limit: int = 50) -> List[str]:
    """Fetch top spot symbols by quote volume (USDT pairs for diversity)."""
    markets = exchange.load_markets()
    usdt_pairs = [s for s in markets if s.endswith('/USDT') and markets[s]['spot']]
    # Sort by inferred volume (fetch ticker for top; limit to 50)
    tickers = exchange.fetch_tickers()
    sorted_pairs = sorted(
        [(s, t['quoteVolume']) for s, t in tickers.items() if s in usdt_pairs],
        key=lambda x: x[1] or 0, reverse=True
    )[:limit]
    return [p[0] for p in sorted_pairs]  # Diverse: High/low vol mix

def fetch_one_history(sym: str, exchange: ccxt.Exchange, days_back: int = 365) -> pd.DataFrame:
    """Fetch 1y 1h OHLCV for symbol."""
    since = int((pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=days_back)).timestamp() * 1000)
    try:
        ohlcv = exchange.fetch_ohlcv(sym, '1h', since=since, limit=1000)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.dropna()
        if len(df) < 100:  # Skip low-data symbols
            return None
        # Relativistic features
        df['change_pct'] = df['close'].pct_change() * 100
        df['volume_pct'] = df['volume'].pct_change() * 100
        df['volatility_pct'] = (df['high'] - df['low']) / df['low'] * 100
        df['sentiment_pct'] = np.random.uniform(40, 70, len(df))  # Placeholder; replace with LunarCrush
        vol_sma = df['volume'].rolling(20).mean()
        df['R'] = np.clip((df['volume_pct'] / (vol_sma / df['volume'].mean() if vol_sma.mean() > 0 else 1)) * 255 / 2, 0, 255).astype(int)
        df['G'] = np.clip(df['sentiment_pct'] * 2.55, 0, 255).astype(int)
        df['B'] = np.clip(df['volatility_pct'] * 25.5, 0, 255).astype(int)
        df['embed_4'] = df['close'].ewm(span=10).mean()  # Line val normalized later
        return df[['R', 'G', 'B', 'embed_4']].values  # RGB + line per bar
    except Exception as e:
        print(f"Failed {sym}: {e}")
        return None

def generate_samples(histories: Dict[str, np.ndarray], seq_len: int = 60, num_per_sym: int = 20) -> torch.Tensor:
    """Window histories to (total_samples, seq_len, 4) for diversity."""
    samples = []
    for sym_data in histories.values():
        if sym_data is None or len(sym_data) < seq_len:
            continue
        # Normalize embed_4 to 0-1
        sym_data[:, 3] = (sym_data[:, 3] - sym_data[:, 3].min()) / (sym_data[:, 3].max() - sym_data[:, 3].min() + 1e-8)
        sym_data[:, :3] /= 255.0  # RGB to 0-1
        for start in np.random.choice(len(sym_data) - seq_len, num_per_sym, replace=False):
            samples.append(sym_data[start:start + seq_len])
    samples = np.array(samples[:1000])  # Cap at 1000 diverse
    return torch.tensor(samples, dtype=torch.float32)  # (1000, 60, 4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="rgb_samples.pt", help="Output tensor file")
    parser.add_argument("--num_samples", type=int, default=1000, help="Target samples")
    parser.add_argument("--api_key", help="MEXC API key (optional for public)")
    parser.add_argument("--secret", help="MEXC secret")
    args = parser.parse_args()
    
    exchange = ccxt.mexc({'apiKey': args.api_key, 'secret': args.secret, 'enableRateLimit': True})
    symbols = get_top_symbols(exchange, 50)  # Diverse top 50
    print(f"Fetching {len(symbols)} symbols...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        histories = dict(executor.map(lambda s: (s, fetch_one_history(s, exchange)), symbols))
    
    tensor = generate_samples({s: h for s, h in histories.items() if h is not None}, num_per_sym=args.num_samples // len([h for h in histories.values() if h is not None]))
    torch.save(tensor, args.output)
    print(f"Saved {len(tensor)} samples to {args.output}")