from apscheduler.schedulers.background import BackgroundScheduler
from portfolio import Portfolio
from data_fetcher import fetch_live_data
from data_processing.technical_analysis import generate_technical_signals  # Assuming this exists in your project

class TradeSimulator:
    def __init__(self, starting_cash, watchlist):
        self.portfolio = Portfolio(starting_cash)
        self.watchlist = watchlist
        self.scheduler = BackgroundScheduler()
        self.running = False

    def start(self):
        if not self.running:
            self.scheduler.add_job(self.simulate_trades, 'interval', minutes=10)
            self.scheduler.start()
            self.running = True

    def stop(self):
        if self.running:
            self.scheduler.shutdown()
            self.running = False

    def reset(self, starting_cash):
        self.stop()
        self.portfolio = Portfolio(starting_cash)

    def simulate_trades(self):
        for symbol in self.watchlist:
            # Fetch recent data for indicators (assuming this function exists)
            data = fetch_historical_data(symbol)
            signals = generate_technical_signals(data, timeframe='short')
            current_price = fetch_live_data(symbol)

            # Define a "strong signal" (customize based on your indicators)
            if signals['sma'].iloc[-1] == 1 and signals['rsi'].iloc[-1] == 1:  # Buy signal
                try:
                    self.portfolio.buy(symbol, quantity=1, price=current_price)
                    print(f"Bought 1 share of {symbol} at {current_price}")
                except ValueError as e:
                    print(e)
            elif signals['sma'].iloc[-1] == -1 and signals['rsi'].iloc[-1] == -1:  # Sell signal
                try:
                    self.portfolio.sell(symbol, quantity=1, price=current_price)
                    print(f"Sold 1 share of {symbol} at {current_price}")
                except ValueError as e:
                    print(e)

# Example usage
if __name__ == "__main__":
    watchlist = ['ABC.TO', 'XYZ.TO']
    simulator = TradeSimulator(starting_cash=400, watchlist=watchlist)
    simulator.start()
