# backtest.py (Fixed Forward Chunking + Momentum)
import logging
import sys
import time
import requests
import sqlite3
from datetime import datetime
import pandas as pd
import numpy as np

from config import ADX_THRESHOLD, ATR_MULT_SL, ATR_MULT_TP, LONG_TF, MONTHLY_BACKTEST
from strategies import evaluate_strategy, calculate_and_enrich_klines

# --- Config ---
SYMBOLS_TO_TEST = ["BTCUSDT", "XRPUSDT", "ETHUSDT", "DASHUSDT", "DOGEUSDT"]
STRATEGIES_TO_TEST = ["HIGH_CONFIDENCE", "BALANCED", "AGGRESSIVE"]
START_DATE = "2024-01-01"
END_DATE = "2024-06-30"
API_INTERVAL = "60m"
INITIAL_CAPITAL = 10000.0
STOP_LOSS_PCT = 0.07
TAKE_PROFIT_PCT = 0.12
DB_FILE = "backtest.db"
TRADE_FEE_PCT = 0.0005
POSITION_SIZE_PCT = 0.02
MAX_HOLD_HOURS = 72  # Longer hold
RISK_FREE_RATE = 0.02
MEXC_API_BASE = "https://api.mexc.com"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)])

def init_db():
    """Initializes the database and creates the klines table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS klines (
                symbol TEXT,
                interval TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                close_time INTEGER,
                quote_volume REAL,
                PRIMARY KEY (symbol, interval, timestamp)
            )
        """)
        conn.commit()

def save_klines_to_db(symbol, interval, klines):
    """Saves a list of klines to the database, ignoring duplicates."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        data_to_insert = [
            (symbol, interval, int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), int(k[6]), float(k[7]))
            for k in klines
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO klines 
            (symbol, interval, timestamp, open, high, low, close, volume, close_time, quote_volume) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data_to_insert)
        conn.commit()
        logging.info(f"Saved {len(data_to_insert)} klines for {symbol} to {DB_FILE}")
def get_long_trend(symbol, tf=LONG_TF):
    """Fetch higher TF (4h/1d) for bull/bear filter: 1 bull (close>SMA200), -1 bear, 0 neutral."""
    klines_htf = get_historical_data(symbol, START_DATE, END_DATE, tf)
    if len(klines_htf) < 200: # Need at least 200 candles for SMA200
        return 0
    df_htf = pd.DataFrame(klines_htf, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'])
    df_htf['close'] = pd.to_numeric(df_htf['close'])
    sma200 = df_htf['close'].rolling(200).mean().iloc[-1]
    close = df_htf['close'].iloc[-1]
    if close > sma200 * 1.01:  # 1% buffer for bullish
        return 1
    elif close < sma200 * 0.99: # 1% buffer for bearish
        return -1
    return 0
def fetch_klines_from_db(symbol, interval, start_ts, end_ts):
    """Fetches klines from the database within a specified time range."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, open, high, low, close, volume, close_time, quote_volume 
            FROM klines 
            WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (symbol, interval, start_ts, end_ts))
        return cursor.fetchall()

def get_historical_data(symbol, start_date_str, end_date_str, interval, monthly_chunks=False):
    """Fetches historical data from DB, falling back to API if needed."""
    start_ts = int(datetime.strptime(start_date_str, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date_str, "%Y-%m-%d").timestamp() * 1000) + 86400000

    logging.info(f"Attempting to fetch data for {symbol} from DB...")
    db_klines = fetch_klines_from_db(symbol, interval, start_ts, end_ts)
    # Check if we have at least 99% of the expected hourly candles
    expected_candles = (end_ts - start_ts) / 3600000
    if db_klines and len(db_klines) > expected_candles * 0.99:
        logging.info(f"Found {len(db_klines)} klines for {symbol} in database. Using cached data.")
        return db_klines

    all_klines = []
    logging.info(f"Insufficient data in DB. Fetching from API for {symbol} ({interval}) from {start_date_str} to {end_date_str}...")

    if monthly_chunks and interval == '15m':
        current_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        while current_date <= end_dt:
            # Calculate month start/end timestamps
            month_start_ts = int(current_date.timestamp() * 1000)
            # Determine end of current month or overall end_dt, whichever is sooner
            next_month_start = (current_date.replace(day=1) + pd.DateOffset(months=1))
            month_end_dt_limit = min(next_month_start - pd.Timedelta(seconds=1), end_dt) # End of day for month
            month_end_ts = int(month_end_dt_limit.timestamp() * 1000)
            
            logging.info(f"Fetching {interval} for {symbol} from {current_date.strftime('%Y-%m-%d')} to {month_end_dt_limit.strftime('%Y-%m-%d')} (monthly chunk)")
            
            current_chunk_start = month_start_ts
            interval_ms = 60000 * 15 # 15m in ms
            
            while current_chunk_start <= month_end_ts:
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': 1000,
                    'startTime': current_chunk_start,
                    'endTime': month_end_ts
                }
                try:
                    response = requests.get(f"{MEXC_API_BASE}/api/v3/klines", params=params)
                    response.raise_for_status()
                    chunk = response.json()
                    if not chunk:
                        break
                    all_klines.extend(chunk)
                    last_time = int(chunk[-1][0])
                    current_chunk_start = last_time + interval_ms
                    logging.debug(f"Fetched {len(chunk)} klines up to {datetime.fromtimestamp(last_time/1000)} for month chunk")
                except requests.exceptions.RequestException as e:
                    logging.error(f"Raw fetch error for month chunk: {e}")
                    break
            current_date = next_month_start # Move to the next month
    else: # Existing logic for non-monthly chunked fetching
        current_start = start_ts
        interval_ms = 3600000 if interval == '1h' else (60000 * 15 if interval == '15m' else 3600000 * 4) # Default to 1h, 15m, or 4h
        
        while current_start < end_ts:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': 1000,
                'startTime': current_start,
                'endTime': end_ts
            }
            try:
                response = requests.get(f"{MEXC_API_BASE}/api/v3/klines", params=params)
                response.raise_for_status()
                chunk = response.json()
                if not chunk:
                    break
                all_klines.extend(chunk)
                last_time = int(chunk[-1][0])
                current_start = last_time + interval_ms
                logging.debug(f"Fetched {len(chunk)} klines up to {datetime.fromtimestamp(last_time/1000)}")
            except requests.exceptions.RequestException as e:
                logging.error(f"Raw fetch error: {e}")
                break
    
    # Dedup/sort
    if all_klines:
        df_temp = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'])
        df_temp['timestamp'] = pd.to_numeric(df_temp['timestamp'])
        df_temp.drop_duplicates('timestamp', inplace=True)
        df_temp.sort_values('timestamp', inplace=True)
        all_klines = df_temp[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume']].values.tolist()
        # Save the newly fetched data to the DB for next time
        save_klines_to_db(symbol, interval, all_klines)

    first, last = all_klines[0][0] if all_klines else 0, all_klines[-1][0] if all_klines else 0
    logging.info(f"Fetched {len(all_klines)} unique klines from {datetime.fromtimestamp(first/1000)} to {datetime.fromtimestamp(last/1000)}")
    return all_klines

# run_backtest (with momentum filter)
def run_backtest(klines, initial_capital, sl_mult, tp_mult, strategy_name, interval, adx_threshold=ADX_THRESHOLD, long_trend_filter=0):
    if len(klines) < 250:
        return [], pd.Series()

    enriched_tuples, enriched_cols = calculate_and_enrich_klines("BACKTEST", klines, interval)
    if not enriched_tuples:
        return [], pd.Series()
    
    # Use the columns returned by the enrichment function
    df = pd.DataFrame(enriched_tuples, columns=enriched_cols)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    cash = initial_capital
    position = None
    trades = []
    portfolio_values = []
    entry_time = None
    trailing_high = 0  # For trailing stop
    
    logging.info(f"Using {strategy_name} strategy with ATR SL Mult: {sl_mult:.2f}, TP Mult: {tp_mult:.2f}, ADX Threshold: {adx_threshold}")
    
    for i in range(len(df)):
        current_price = df['close'].iloc[i]
        portfolio_value = cash + (position['quantity'] * current_price if position else 0)
        portfolio_values.append(portfolio_value)
        
        if i < 250:
            continue
        
        df_slice = df.iloc[:i+1]
        result = evaluate_strategy(df_slice, strategy_name)
        prob_score = result.get('prob_score', 0)
        momentum = df_slice['momentum_roc'].iloc[-1] if 'momentum_roc' in df_slice and not pd.isna(df_slice['momentum_roc'].iloc[-1]) else 0
        prev_momentum = df_slice['momentum_roc'].iloc[-2] if len(df_slice) > 1 and 'momentum_roc' in df_slice and not pd.isna(df_slice['momentum_roc'].iloc[-2]) else momentum

        # New variables for dynamic SL/TP and filtering
        atr = df_slice['atr'].iloc[-1] if 'atr' in df_slice and not pd.isna(df_slice['atr'].iloc[-1]) else current_price * 0.05
        adx = df_slice['adx'].iloc[-1] if 'adx' in df_slice and not pd.isna(df_slice['adx'].iloc[-1]) else 0
        volatility_1h = df_slice['volatility_1h'].iloc[-1] if 'volatility_1h' in df_slice and not pd.isna(df_slice['volatility_1h'].iloc[-1]) else 0

        if position is None:
            # Enhanced entry: MA cross implied in result; add vol filter
            vol_ratio = df_slice['vol_ratio_5'].iloc[-1] if 'vol_ratio_5' in df_slice and not pd.isna(df_slice['vol_ratio_5'].iloc[-1]) else 0
            is_trending = adx > adx_threshold and volatility_1h > 0.03 # Volatility filter
            if result['signal'] and prob_score > 0.5 and momentum > -0.5 and prev_momentum > momentum and vol_ratio > 1.2 and is_trending:
                position_size = (portfolio_value * POSITION_SIZE_PCT) * (1 + result.get('confidence', 0.0))  # Scale by confidence
                quantity = position_size / current_price
                cost = quantity * current_price
                cost *= (1 + 0.001)  # Slippage
                fee = cost * TRADE_FEE_PCT
                if cost + fee < cash:
                    cash -= (cost + fee)
                    position = {'entry_price': current_price, 'quantity': quantity}
                    trailing_high = current_price
                    entry_time = df_slice.index[-1]
                    trades.append({'type': 'buy', 'price': current_price, 'time': entry_time, 'quantity': quantity})
                    logging.debug(f"BUY at {current_price:.4f} | Prob: {prob_score:.2f} | Momentum: {momentum:.2f}% (slowing)")
        elif position:
            hold_hours = (df.index[i] - entry_time).total_seconds() / 3600 if entry_time else 0
            
            # Dynamic SL/TP with ATR
            sl_price = position['entry_price'] - (atr * sl_mult)
            tp_price = position['entry_price'] + (atr * tp_mult)
            
            # Trailing stop: Update high, trail 3%
            if current_price > trailing_high:
                trailing_high = current_price
            trail_stop = trailing_high * (1 - 0.03)
            
            sell = (current_price >= tp_price or current_price <= sl_price or 
                    current_price <= trail_stop or hold_hours >= MAX_HOLD_HOURS or 
                    result['prob_score'] < -0.2)  # Exit on bear signal
            if sell:
                exit_value = position['quantity'] * current_price
                exit_value *= (1 - 0.001)  # Slippage
                exit_fee = exit_value * TRADE_FEE_PCT  # Add fee here
                cash += (exit_value - exit_fee)
                net_pnl_pct = ((exit_value - exit_fee) / (position['quantity'] * position['entry_price'])) - 1
                trades[-1].update({'exit_price': current_price, 'exit_time': df.index[i], 'pnl_pct': net_pnl_pct})
                logging.debug(f"SELL at {current_price:.4f} | PnL: {net_pnl_pct:.2%} | Hold: {hold_hours:.1f}h | Reason: {'TP' if current_price >= tp_price else 'SL/Trail'}")
                position = None
                entry_time = None
    
    # Close open position at end
    if position:
        exit_value = position['quantity'] * df['close'].iloc[-1]
        exit_fee = exit_value * TRADE_FEE_PCT
        cash += (exit_value - exit_fee)
        net_pnl_pct = ((exit_value - exit_fee) / (position['quantity'] * position['entry_price'])) - 1
        trades[-1].update({'exit_price': df['close'].iloc[-1], 'exit_time': df.index[-1], 'pnl_pct': net_pnl_pct})
    
    return trades, pd.Series(portfolio_values, index=df.index)

def calculate_and_print_metrics(symbol, portfolio, trades, initial_capital, strategy_name, sl_mult, tp_mult, adx_threshold):
    """Calculates and prints a full performance report for a backtest run."""
    if portfolio.empty:
        logging.warning(f"Portfolio for {symbol} is empty. Cannot generate metrics.")
        return

    # --- Portfolio Metrics ---
    final_capital = portfolio.iloc[-1]
    total_return = (final_capital / initial_capital) - 1

    # Calculate returns for Sharpe Ratio
    returns = portfolio.pct_change().dropna()
    
    # Annualize Sharpe Ratio (crypto trades 24/7/365)
    trading_periods_per_year = 24 * 365 
    if returns.std() > 0:
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(trading_periods_per_year) if returns.mean() != 0 else 0.0
    else:
        sharpe_ratio = 0.0

    # Max Drawdown
    rolling_max = portfolio.cummax()
    drawdown = (portfolio - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    # Calmar Ratio
    annualized_return = total_return * (trading_periods_per_year / len(portfolio)) if len(portfolio) > 0 else 0.0
    calmar_ratio = (annualized_return / abs(max_drawdown)) if max_drawdown != 0 else 0.0

    # --- Trade Metrics ---
    total_trades = len(trades)
    if total_trades > 0:
        pnl_values = [t['pnl_pct'] for t in trades if 'pnl_pct' in t]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p <= 0]
        
        win_rate = (len(wins) / total_trades) if total_trades > 0 else 0.0
        
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    else:
        win_rate = 0.0
        profit_factor = float('inf')

    # --- Print Report ---
    print("\n--- Backtest Results ---")
    print(f"Symbol: {symbol}")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Strategy: {strategy_name} (SL: {sl_mult:.2f}, TP: {tp_mult:.2f}, ADX: {adx_threshold})")
    print("--------------------------------------------------")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Capital:   ${final_capital:,.2f}")
    print(f"Total Return:    {total_return:.2%}")
    print(f"Sharpe Ratio:    {sharpe_ratio:.2f}")
    print(f"Max Drawdown:    {max_drawdown:.2%}")
    print(f"Calmar Ratio:    {calmar_ratio:.2f}")
    print("--------------------------------------------------")
    print(f"Total Trades:    {total_trades}")
    print(f"Win Rate:        {win_rate:.2%}")
    print(f"Profit Factor:   {profit_factor:.2f}")
    print("--- End of Report ---")

    return {
        'symbol': symbol, 'strategy': strategy_name, 'sl_mult': sl_mult, 'tp_mult': tp_mult, 'adx_threshold': adx_threshold,
        'return': total_return, 'sharpe': sharpe_ratio, 'max_drawdown': max_drawdown,
        'trades': total_trades, 'win_rate': win_rate, 'profit_factor': profit_factor
    }

def main():
    # Initialize the database
    init_db()

    # Grid search example
    sl_multipliers = [1.0, 1.5, 2.0, 2.5]  # ATR multipliers for Stop Loss
    tp_multipliers = [1.5, 2.0, 2.5, 3.0]  # ATR multipliers for Take Profit
    adx_thresholds = [20, 25, 30]          # ADX trend strength filter
    all_results = []

    for strategy_name in STRATEGIES_TO_TEST:
        for symbol in SYMBOLS_TO_TEST:
            print(f"\n===== Running Grid Search for {symbol} on {strategy_name} =====")
            
            is_monthly_chunk_interval = (API_INTERVAL == '15m' and MONTHLY_BACKTEST)
            klines = get_historical_data(symbol, START_DATE, END_DATE, API_INTERVAL, monthly_chunks=is_monthly_chunk_interval)
            if not klines or len(klines) < 250:
                logging.error(f"Insufficient data for {symbol}. Skipping.")
                continue
            
            long_trend = get_long_trend(symbol, LONG_TF)
            if long_trend < 0:
                logging.info(f"Bear trend detected on higher TF ({LONG_TF}) for {symbol}. Skipping backtest for this symbol.")
                continue
            # Grid search over ATR multipliers
            for sl in sl_multipliers:
                for tp in tp_multipliers:
                    for adx in adx_thresholds:
                        trades, portfolio = run_backtest(klines, INITIAL_CAPITAL, sl, tp, strategy_name, API_INTERVAL, adx_threshold=adx, long_trend_filter=long_trend)
                        metrics = calculate_and_print_metrics(symbol, portfolio, trades, INITIAL_CAPITAL, strategy_name, sl, tp, adx)
                        if metrics:
                            all_results.append(metrics)
    
    if all_results:
        df_grid = pd.DataFrame(all_results).sort_values('sharpe', ascending=False)

        # Filter for profitable runs to save to CSV
        profitable_runs_df = df_grid[df_grid['return'] > 0]
        
        # Save only profitable results to a CSV file
        results_filename = "grid_search_results.csv"
        profitable_runs_df.to_csv(results_filename, index=False)
        print(f"\n\nSaved {len(profitable_runs_df)} profitable runs to {results_filename}")

        # Display top results from ALL runs in the console
        print("\n--- Top 50 Grid Search Results (by Sharpe Ratio) ---")
        print(df_grid.head(50))

if __name__ == "__main__":
    main()