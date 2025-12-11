# main.py
import os
import time
import sys
import signal
import logging
from typing import List, Dict, Any, Optional
import pandas as pd  # For strategies
import schedule
from config import (DB_FILE, SCAN_BATCH_SIZE, SCAN_INTERVAL, MAX_KLINES_FAILURES, 
                    KLINE_HISTORY_DAYS, VOLUME_THRESHOLD, STRATEGY)
import config
from db import (create_tables, init_symbols_db, get_all_symbols, save_signal, prune_old_klines,
               get_active_symbols_with_history, insert_top_symbols, get_latest_top_symbols, save_klines_by_interval)
from api import api
from strategies import get_buy_signal, calculate_and_enrich_klines, evaluate_strategy, get_strategy_metrics

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    logging.info("\nShutting down bot gracefully...")
    running = False

# --- Multi-Timeframe Scanning Logic ---

TOP_20_15M = [] # Global to hold top candidates from 15m poll

def initial_kline_population():
    """
    Performs a one-time scan to populate the klines_1h table for all active symbols.
    This is necessary on the first run when no historical data exists.
    """
    logging.info("Performing initial kline data population for 1h timeframe...")
    all_symbols = get_all_symbols()
    total_symbols = len(all_symbols)
    
    for i, symbol in enumerate(all_symbols):
        progress_message = f"--> Initial Population {i + 1}/{total_symbols}: {symbol:<15}"
        sys.stdout.write(f"\r{progress_message}")
        sys.stdout.flush()
        try:
            # Fetch enough data to satisfy the history check
            klines = api.get_klines(symbol, interval='60m', limit=210)
            if klines:
                enriched_data, enriched_cols = calculate_and_enrich_klines(symbol, klines, interval='1h')
                save_klines_by_interval('1h', enriched_data, enriched_cols)
        except Exception as e:
            # Using debug level to avoid flooding console on first run if many symbols fail
            logging.debug(f"Error during initial population for {symbol}: {e}")
            continue
            
    sys.stdout.write("\r" + " " * 80 + "\r") # Clear progress line
    sys.stdout.flush()
    logging.info("Initial kline data population complete.")

def hourly_scan():
    """Full 1h scan: Filter history, compute probs, rank top 100."""
    symbols = get_active_symbols_with_history(200, '1h')
    logging.info(f"Hourly scan starting for {len(symbols)} symbols with >=200h history.")
    top_candidates = []
    for i, symbol in enumerate(symbols):
        progress_message = f"--> Hourly Scan {i + 1}/{len(symbols)}: {symbol:<15}"
        sys.stdout.write(f"\r{progress_message}")
        sys.stdout.flush()
        try:
            klines = api.get_klines(symbol, interval='60m', limit=210)
            enriched_data, enriched_cols = calculate_and_enrich_klines(symbol, klines, interval='1h')
            save_klines_by_interval('1h', enriched_data, enriched_cols)
            
            df = pd.DataFrame(enriched_data, columns=enriched_cols)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            result = evaluate_strategy(df, config.STRATEGY)
            if result['prob_score'] > 0:  # Positive bias
                top_candidates.append({'symbol': symbol, 'prob_score': result['prob_score'], 'confidence': result['confidence']})
        except Exception as e:
            logging.error(f"Hourly error for {symbol}: {e}")
            continue
    
    sys.stdout.write("\r" + " " * 80 + "\r") # Clear progress line
    sys.stdout.flush()

    # Rank and save top 100
    if top_candidates:
        top_100 = sorted(top_candidates, key=lambda x: x['prob_score'], reverse=True)[:100]
        top_list = [{'symbol': item['symbol'], 'prob_score': item['prob_score'], 'rank': i+1} for i, item in enumerate(top_100)]
        insert_top_symbols(top_list)
        logging.info(f"Hourly scan complete: Top 100 saved. Highest prob: {top_100[0]['prob_score']:.2f}")
    else:
        logging.info("Hourly scan complete: No promising candidates found.")

def poll_15m():
    """Poll top 100 on 15m: Update data, re-rank top 20."""
    global TOP_20_15M
    top_100 = get_latest_top_symbols(100)
    if not top_100:
        logging.info("15m poll: No top symbols from hourly scan to process.")
        return
    
    logging.info(f"15m poll: Updating {len(top_100)} top symbols.")
    top_20_candidates = []
    for item in top_100:
        symbol = item['symbol']
        try:
            klines = api.get_klines(symbol, interval='15m', limit=100)  # Shorter history
            enriched_data, enriched_cols = calculate_and_enrich_klines(symbol, klines, interval='15m')
            save_klines_by_interval('15m', enriched_data, enriched_cols)
            
            df = pd.DataFrame(enriched_data, columns=enriched_cols)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            result = evaluate_strategy(df, config.STRATEGY)  # Refine prob with 15m data
            if result['prob_score'] > 0.4:  # Threshold for top 20
                top_20_candidates.append({'symbol': symbol, 'prob_score': result['prob_score']})
        except Exception as e:
            logging.error(f"15m error for {symbol}: {e}")
            continue
            
    TOP_20_15M = sorted(top_20_candidates, key=lambda x: x['prob_score'], reverse=True)[:20]
    if TOP_20_15M:
        logging.info(f"15m poll complete: Top 20 ranked. Highest prob: {TOP_20_15M[0]['prob_score']:.2f}")
    else:
        logging.info("15m poll complete: No candidates met the threshold for the top 20.")

def poll_5m_confirm():
    """5m momentum check on top 20: Trigger buys if flat/slowing."""
    global TOP_20_15M
    if not TOP_20_15M:
        logging.debug("5m confirm: No candidates from 15m poll to check.")
        return
        
    logging.info(f"5m confirm: Checking momentum on {len(TOP_20_15M)} candidates.")
    for item in TOP_20_15M:
        symbol = item['symbol']
        try:
            klines = api.get_klines(symbol, interval='5m', limit=50)  # Short for momentum
            enriched_data, enriched_cols = calculate_and_enrich_klines(symbol, klines, interval='5m')
            save_klines_by_interval('5m', enriched_data, enriched_cols)
            
            df = pd.DataFrame(enriched_data, columns=enriched_cols)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            momentum = df['momentum_roc'].iloc[-1] if 'momentum_roc' in df and not pd.isna(df['momentum_roc'].iloc[-1]) else 0
            if momentum >= 0:  # Flat/slowing up (not down)
                current_price = float(api.get_price(symbol)['price'])
                sl = current_price * 0.95  # 5% stop
                tp = current_price * 1.10  # 10% take
                logging.info(f"BUY TRIGGER: {symbol} at ${current_price:.4f} | Momentum: {momentum:.2f}% | SL: ${sl:.4f}, TP: ${tp:.4f}")
                metrics = get_strategy_metrics(df)
                save_signal(symbol, current_price, 0, config.STRATEGY, metrics, [], item['prob_score'], 0)
        except Exception as e:
            logging.error(f"5m error for {symbol}: {e}")
            continue
    logging.info("5m confirm complete.")

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

    # --- Initial Data Population Check ---
    # If no symbols have enough history, run a one-time scan to populate the DB.
    symbols_with_history = get_active_symbols_with_history(200, '1h')
    if not symbols_with_history:
        logging.warning("No symbols with sufficient 1h kline history found. Starting initial data population...")
        initial_kline_population()
        
        # After populating 1h data, run an initial hourly scan to get top symbols
        logging.info("Running initial hourly scan to rank symbols...")
        hourly_scan()
        # After ranking, run an initial 15m poll to populate its data
        logging.info("Running initial 15m poll for top symbols...")
        poll_15m()
    
    # --- Schedule Jobs ---
    logging.info("Scheduling scanning jobs...")
    schedule.every().hour.at(":01").do(hourly_scan) # Run 1 min past the hour
    schedule.every(15).minutes.do(poll_15m)
    schedule.every(5).minutes.do(poll_5m_confirm)

    prune_old_klines(KLINE_HISTORY_DAYS)  # Initial prune on startup

    logging.info("Scheduler started. Waiting for jobs...")
    while running:
        schedule.run_pending()
        time.sleep(1) # Sleep to prevent high CPU usage

    logging.info("Bot stopped.")

if __name__ == "__main__":
    main()