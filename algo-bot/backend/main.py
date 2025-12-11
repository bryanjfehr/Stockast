# main.py
import os
import time
import sys
import signal
import logging
from typing import List, Dict, Any
import pandas as pd  # For strategies
from config import DB_FILE, SCAN_BATCH_SIZE, SCAN_INTERVAL, MAX_KLINES_FAILURES, KLINE_HISTORY_DAYS
from db import (create_tables, init_symbols_db, get_all_symbols, save_klines,
               increment_klines_fail_count, reset_klines_fail_count, save_signal, prune_old_klines)
from api import api
from strategies import get_buy_signal, get_signal_metrics, calculate_and_enrich_klines

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    logging.info("\nShutting down bot gracefully...")
    running = False

def scan_batch(batch_symbols: List[str]):
    """
    Scan a batch of symbols: Fetch klines, check signal, log potentials.
    """
    signals_found_in_batch = 0
    
    # Fetch all 24hr ticker data once for efficiency
    logging.info("Fetching all 24hr ticker data...")
    all_tickers_data = api.get_ticker_24hr()
    if isinstance(all_tickers_data, dict): # If only one ticker was returned (e.g. if symbol was specified as None but only one exists)
        all_tickers_data = [all_tickers_data]
    ticker_map = {ticker['symbol']: ticker for ticker in all_tickers_data}

    total_symbols = len(batch_symbols)
    for i, symbol in enumerate(batch_symbols):
        progress_message = f"--> Scanning {i + 1}/{total_symbols}: {symbol:<15}"
        sys.stdout.write(f"\r{progress_message}")
        sys.stdout.flush()
        try:
            # Fetch klines for each symbol synchronously. The _request method handles the delay.
            # We need at least 201 data points for a 200-period crossover check. Fetching a bit more is safer.
            klines = api.get_klines(symbol, interval='60m', limit=210)
            
            # Calculate indicators and prepare for DB
            enriched_klines = calculate_and_enrich_klines(symbol, klines)
            
            # If klines were successfully fetched, reset the failure count
            reset_klines_fail_count(symbol)
            save_klines(enriched_klines)

            # Check strategy signal
            signal_result = get_buy_signal(klines, strategy='MA_RSI_COMBO')
            if signal_result.get('signal'):
                # Clear the progress line before printing the signal
                sys.stdout.write("\r" + " " * len(progress_message) + "\r")
                sys.stdout.flush()

                metrics = get_signal_metrics(klines)
                if metrics:
                    logging.debug(f"Signal metrics for {symbol}: RSI={metrics['rsi']:.1f}, MA Diff={metrics['ma_diff_pct']:.2f}%, Fib Bounce={metrics.get('fib_bounce_pct', 0):.2f}%")

                # Check liquidity (volume filter)
                ticker = ticker_map.get(symbol)
                VOLUME_THRESHOLD = 100000 # Min $100k 24hr volume filter
                if ticker and 'quoteVolume' in ticker and ticker['quoteVolume'] is not None:
                    volume = float(ticker['quoteVolume'])
                    if volume > VOLUME_THRESHOLD:
                        # Fetch current price (this is a single call, could be optimized if needed)
                        current_price_data = api.get_price(symbol)
                        current_price = float(current_price_data['price']) if current_price_data and 'price' in current_price_data else 0.0

                        strategy_name = '+'.join(signal_result['active_indicators']) if signal_result['active_indicators'] else "UNKNOWN"
                        logging.info(f"BUY SIGNAL: {symbol} at ${current_price:.4f} (24hr Vol: ${volume:,.2f}) | Indicators: {strategy_name} | Strength: {signal_result['strength']:.2f}")
                        save_signal(symbol, current_price, volume, strategy_name, metrics, signal_result['active_indicators'])
                        signals_found_in_batch += 1
                else:
                    logging.debug(f"Signal for {symbol} but 24hr ticker data or quoteVolume missing. Skipping.")

        except ValueError as e: # This is the error raised by our _request method on API/HTTP failure
            logging.debug(f"Skipping {symbol}: Kline fetch failed: {e}. Incrementing failure count.")
            increment_klines_fail_count(symbol)
            continue
        except Exception as e:
            logging.error(f"Error processing strategy for {symbol}: {e}", exc_info=True)
            continue  # Skip on error, don't halt batch
    
    # After the loop, clear the progress line.
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

    if signals_found_in_batch > 0:
        logging.info(f"Batch scan complete: {signals_found_in_batch} potential buys found and saved to DB.")
    else:
        logging.info(f"Batch scan complete: No signals.")

def main():
    """
    Main entry point for the trading bot.
    """
    global running
    signal.signal(signal.SIGINT, signal_handler)  # Handle Ctrl+C

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("Starting trading bot...")

    # Initialize database first
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        logging.info("Database not found or empty, initializing...")
        create_tables()
        init_symbols_db()
    else:
        logging.info("Database found.")

    # --- API Health Check ---
    # Perform a single, simple API call to ensure the klines endpoint is accessible.
    # This fails fast if there's a fundamental issue like invalid API key permissions.
    try:
        logging.info("Performing API health check on klines endpoint...")
        api.get_klines("BTCUSDT", interval="60m", limit=1)
        logging.info("API health check passed. Kline data is accessible.")
    except Exception as e:
        logging.error(f"API health check FAILED: {e}", exc_info=False)
        logging.error(
            "This is likely due to an invalid API key or missing 'Read' permissions for your key. "
            "Please go to MEXC, check your API key permissions, and ensure it can access market data. Exiting."
        )
        return # Stop the bot if the health check fails

    # --- Main Menu ---
    while True:
        print("\nSelect one of the following options:")
        print("1: Begin scanning for signals")
        print("2: Begin paper trading (in development)")
        print("3: Define strategy for live trading (in development)")
        print("4: Options (in development)")
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            break  # Proceed to scanning
        elif choice in ['2', '3', '4']:
            print(f"Option {choice} is in development. Exiting program.")
            return
        else:
            print("Invalid choice, please try again.")

    # Get symbols
    symbols = get_all_symbols()
    logging.info(f"Loaded {len(symbols)} active symbols from the database (excluding those with too many kline fetch failures).")

    # Main scanning loop
    logging.info("Starting scanning loop. Press Ctrl+C to stop.")
    batch_size = SCAN_BATCH_SIZE  # e.g., 50
    while running:
        for i in range(0, len(symbols), batch_size):
            if not running:
                break
            batch = symbols[i:i + batch_size]
            logging.info(f"Scanning batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1} ({len(batch)} symbols)...")
            scan_batch(batch)
            time.sleep(SCAN_INTERVAL)  # 60s between batches
        
        if running:
            # Prune old kline data after each full cycle
            prune_old_klines(KLINE_HISTORY_DAYS)
            
            logging.info("Full scan cycle complete. Restarting in 60s...")
            time.sleep(60)  # Pause between full cycles

    logging.info("Bot stopped.")

if __name__ == "__main__":
    main()