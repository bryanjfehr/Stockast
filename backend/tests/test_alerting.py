import unittest
from unittest.mock import patch, call
from collections import namedtuple
from alert_generator import generate_signals, process_stock
from notification import send_alert

# Define a mock StockPrice object for testing
StockPriceMock = namedtuple('StockPrice', ['date', 'close'])

class TestAlerting(unittest.TestCase):

    def test_generate_signals_buy(self):
        """
        Test that a buy signal is generated correctly for MA Crossover.
        """
        # Setup mock prices to trigger MA Crossover buy signal
        closes = [100.0] * 15 + [90.0] * 4 + [141.0]  # Prices that cause short MA to cross above long MA
        mock_prices = [StockPriceMock(date=f'2023-01-{i+1:02d}', close=closes[i]) for i in range(20)]
        symbol = 'TEST'
        signals = generate_signals(symbol, mock_prices)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]['signal'], 'BUY')
        self.assertEqual(signals[0]['indicator'], 'MA Crossover')
        self.assertEqual(signals[0]['price'], 141.0)

    def test_generate_signals_no_data(self):
        """
        Test that no signals are generated when there is insufficient data.
        """
        symbol = 'TEST'
        mock_prices = []  # Empty list to simulate insufficient data
        signals = generate_signals(symbol, mock_prices)
        self.assertEqual(len(signals), 0)

    @patch('notification.send_email')
    @patch('notification.send_sms')
    def test_send_alert(self, mock_send_sms, mock_send_email):
        """
        Test that send_alert calls both send_email and send_sms with the correct message.
        """
        message = "Test signal for TEST: BUY at 100.00"
        send_alert(message)
        mock_send_email.assert_called_once_with("Stock Trading Alert", message)
        mock_send_sms.assert_called_once_with(message)

    @patch('alert_generator.get_stock_prices')
    @patch('notification.send_alert')
    def test_process_stock_with_signals(self, mock_send_alert, mock_get_stock_prices):
        """
        Test that process_stock generates signals and sends alerts correctly.
        """
        # Setup mock prices to trigger MA Crossover buy signal
        closes = [100.0] * 15 + [90.0] * 4 + [141.0]
        mock_prices = [StockPriceMock(date=f'2023-01-{i+1:02d}', close=closes[i]) for i in range(20)]
        mock_get_stock_prices.return_value = mock_prices
        symbol = 'TEST'
        process_stock(symbol)
        mock_send_alert.assert_called_once_with(f"MA Crossover signal for {symbol}: BUY at 141.0")

    @patch('alert_generator.get_stock_prices')
    @patch('notification.send_alert')
    def test_process_stock_no_signals(self, mock_send_alert, mock_get_stock_prices):
        """
        Test that process_stock does not send alerts when no signals are generated.
        """
        # Setup mock prices that do not trigger any signals
        closes = [100.0] * 20  # Constant prices, no crossovers or extreme RSI/BB values
        mock_prices = [StockPriceMock(date=f'2023-01-{i+1:02d}', close=closes[i]) for i in range(20)]
        mock_get_stock_prices.return_value = mock_prices
        symbol = 'TEST'
        process_stock(symbol)
        mock_send_alert.assert_not_called()

if __name__ == '__main__':
    unittest.main()
