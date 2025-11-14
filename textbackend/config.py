INTERVALS = {
    'trend': '1h',
    'entry_exit': ['5m', '15m'],
    'indicators': ['15m', '60m']
}
SL_TP_PERCENT = 0.05  # 5%
WIN_RATE_THRESHOLD = 0.95
SYMBOLS_ENDPOINT = '/api/v3/exchangeInfo'
SHORT_POLL = 60  # seconds
FEE_RATE = 0.0005  # 0.05% taker default
RISK_MAX_PERCENT = 0.05  # 5% of reserves
SUCCESS_THRESHOLD = 0.90  # >90%
MIN_RISK_DOLLAR = 1.0  # Arbitrary min to cover tiny fees, adjustable
BALANCE_QUOTE = 'USDT'  # Assume USDT reserves for sizing
RSI_OVERSOLD = 20
MACD_HIST_SLOPE_THRESHOLD = 0.0  # For leveling/direction change
TP_SL_BASE_PERCENT = 0.05
TP_SL_MAX_PERCENT = 0.15
TRAILING_SL_PROFIT_LOCK = 0.15
MOMENTUM_THRESHOLD = 2.0  # E.g., MACD hist multiplier for 'large' detection