# backtest.py
import logging
import sys
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from api import api
from strategies import get_buy_signal, klines_to_dataframe

# --- Backtest Configuration ---
# NOTE: Your .env file must contain a valid (even if permissionless) MEXC_API_KEY
# for the api object to initialize correctly.
SYMBOL_TO_TEST = "BTCUSDT"
START_DATE = "2023-01-01"
END_DATE = "2023-12-31"
INTERVAL = "60m"
INITIAL_CAPITAL = 10000.0
STOP_LOSS_PCT = 0.05  # 5%
TAKE_PROFIT_PCT = 0.10 # 10%
STRATEGY = "MA_CROSSOVER"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def fetch_historical_data(symbol, start_date_str, end_date_str, interval):
    """
    Fetches historical kline data from MEXC in chunks.
    """
    logging.info(f"Fetching historical data for {symbol} from {start_date_str} to {end_date_str}...")
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    current_start_time = int(start_dt.timestamp() * 1000)
    end_timestamp = int(end_dt.timestamp() * 1000)
    
    all_klines = []
    
    while current_start_time < end_timestamp:
        try:
            chunk = api.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=current_start_time,
                limit=1000
            )
            if not chunk:
                logging.info("No more data returned from API. Ending fetch.")
                break
            
            all_klines.extend(chunk)
            last_kline_time = int(chunk[-1][0])
            
            # Move to the next chunk
            current_start_time = last_kline_time + 1
            
            first_date = datetime.fromtimestamp(int(chunk[0][0]) / 1000)
            last_date = datetime.fromtimestamp(last_kline_time / 1000)
            logging.info(f"Fetched {len(chunk)} klines from {first_date} to {last_date}")
            
            # Be nice to the API
            time.sleep(0.2)

        except ValueError as e:
            logging.error(f"Failed to fetch data chunk: {e}")
            break
            
    # Remove duplicates and sort
    if all_klines:
        df = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume'])
        df.drop_duplicates(subset=['timestamp'], inplace=True)
        df.sort_values('timestamp', inplace=True)
        return df.values.tolist()
        
    return []

def run_backtest(klines, initial_capital, stop_loss_pct, take_profit_pct, strategy):
    """
    Simulates a trading strategy on historical data.
    """
    if not klines:
        logging.error("Cannot run backtest, no kline data provided.")
        return [], pd.Series()

    df = klines_to_dataframe(klines)
    capital = initial_capital
    position = None  # To store entry price and time
    trades = []
    portfolio_values = []

    logging.info("Starting trade simulation...")
    for i in range(len(klines)):
        # We need enough history for the strategy to work
        if i < 210: # Minimum data for 200-period MA
            portfolio_values.append(capital)
            continue

        historical_klines_slice = klines[:i+1]
        current_price = float(klines[i][4]) # Close price

        if position is None:
            # Check for a buy signal
            if get_buy_signal(historical_klines_slice, strategy=strategy):
                position = {'entry_price': current_price, 'entry_time': df.index[i]}
                trades.append({'type': 'buy', 'price': current_price, 'time': df.index[i]})
                logging.debug(f"BUY at {current_price} on {df.index[i]}")
        else:
            # Check for sell conditions (take profit or stop loss)
            pnl_pct = (current_price / position['entry_price']) - 1
            
            if pnl_pct >= take_profit_pct or pnl_pct <= -stop_loss_pct:
                capital *= (1 + pnl_pct)
                trades[-1].update({
                    'exit_price': current_price, 
                    'exit_time': df.index[i],
                    'pnl_pct': pnl_pct
                })
                logging.debug(f"SELL at {current_price} on {df.index[i]}, PnL: {pnl_pct:.2%}")
                position = None

        portfolio_values.append(capital)

    return trades, pd.Series(portfolio_values, index=df.index)

def calculate_and_print_metrics(portfolio_history, trades, initial_capital, interval):
    """
    Calculates and prints key performance metrics.
    """
    if portfolio_history.empty:
        logging.warning("Portfolio history is empty, cannot calculate metrics.")
        return

    # --- Time-based calculations ---
    if interval == '60m':
        periods_per_year = 365 * 24
    elif interval == '1d':
        periods_per_year = 365
    else:
        periods_per_year = 252 # Default for daily stock data

    # --- Returns and Ratios ---
    final_capital = portfolio_history.iloc[-1]
    total_return_pct = (final_capital / initial_capital - 1) * 100
    period_returns = portfolio_history.pct_change().dropna()
    
    sharpe_ratio = 0
    if period_returns.std() != 0:
        sharpe_ratio = (period_returns.mean() / period_returns.std()) * np.sqrt(periods_per_year)

    # --- Drawdown ---
    cumulative_returns = (1 + period_returns).cumprod()
    peak = cumulative_returns.cummax()
    drawdown = (cumulative_returns - peak) / peak
    max_drawdown_pct = drawdown.min() * 100

    # --- Trade Stats ---
    completed_trades = [t for t in trades if 'exit_price' in t]
    wins = [t for t in completed_trades if t.get('pnl_pct', 0) > 0]
    losses = [t for t in completed_trades if t.get('pnl_pct', 0) < 0]
    
    win_rate = len(wins) / len(completed_trades) * 100 if completed_trades else 0
    total_profit = sum(t['pnl_pct'] for t in wins)
    total_loss = abs(sum(t['pnl_pct'] for t in losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    # --- Print Report ---
    print("\n--- Backtest Results ---")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Strategy: {STRATEGY} (SL: {STOP_LOSS_PCT:.1%}, TP: {TAKE_PROFIT_PCT:.1%})")
    print("-" * 26)
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Final Capital:   ${final_capital:,.2f}")
    print(f"Total Return:    {total_return_pct:.2f}%")
    print(f"Sharpe Ratio (Annualized): {sharpe_ratio:.2f}")
    print(f"Max Drawdown:    {max_drawdown_pct:.2f}%")
    print("-" * 26)
    print(f"Total Trades:    {len(completed_trades)}")
    print(f"Win Rate:        {win_rate:.2f}%")
    print(f"Profit Factor:   {profit_factor:.2f}")
    print("--- End of Report ---\n")

def main():
    """Main function to run the backtest."""
    klines = fetch_historical_data(SYMBOL_TO_TEST, START_DATE, END_DATE, INTERVAL)
    if not klines:
        logging.error("Failed to fetch historical data. Exiting.")
        return

    trades, portfolio_history = run_backtest(klines, INITIAL_CAPITAL, STOP_LOSS_PCT, TAKE_PROFIT_PCT, STRATEGY)
    calculate_and_print_metrics(portfolio_history, trades, INITIAL_CAPITAL, INTERVAL)

if __name__ == "__main__":
    main()