import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

from sqlalchemy.orm import Session

from app.crud import crud_stock
from app.models import simulation as models
from app.schemas import simulation as schemas

logger = logging.getLogger(__name__)


def calculate_performance_history(
    db: Session, simulation: models.Simulation, trades: List[models.Trade]
) -> List[schemas.PerformancePoint]:
    """
    Generates a time-series of portfolio values for performance charting.

    Args:
        db: The database session.
        simulation: The simulation object.
        trades: A list of all trades executed in the simulation.

    Returns:
        A list of PerformancePoint objects representing the portfolio value over time.
    """
    performance_history: List[schemas.PerformancePoint] = []
    start_date = simulation.start_date.date()
    end_date = date.today()

    if not trades:
        # If no trades, the portfolio value is constant at the initial capital.
        current_date = start_date
        while current_date <= end_date:
            performance_history.append(
                schemas.PerformancePoint(
                    timestamp=current_date,
                    portfolio_value=simulation.initial_capital
                )
            )
            current_date += timedelta(days=1)
        return performance_history

    # 1. Extract unique symbols and fetch all historical data at once
    symbols = list(set(trade.symbol for trade in trades))
    all_historical_data: Dict[str, Dict[date, float]] = {}
    for symbol in symbols:
        historical_data_points = crud_stock.get_historical_data(db, symbol=symbol)
        all_historical_data[symbol] = {
            data.date: data.close for data in historical_data_points
        }

    # 2. Initialize simulation state
    current_capital = simulation.initial_capital
    current_holdings: Dict[str, int] = {}
    sorted_trades = sorted(trades, key=lambda t: t.timestamp)
    trade_index = 0

    # 3. Loop from start_date to end_date, calculating portfolio value daily
    current_date = start_date
    while current_date <= end_date:
        # a. Process trades that occurred on the current_date
        while (
            trade_index < len(sorted_trades)
            and sorted_trades[trade_index].timestamp.date() == current_date
        ):
            trade = sorted_trades[trade_index]
            if trade.action == 'BUY':
                current_capital -= trade.quantity * trade.price + trade.fee
                current_holdings[trade.symbol] = (
                    current_holdings.get(trade.symbol, 0) + trade.quantity
                )
            elif trade.action == 'SELL':
                current_capital += trade.quantity * trade.price - trade.fee
                current_holdings[trade.symbol] = (
                    current_holdings.get(trade.symbol, 0) - trade.quantity
                )
                if current_holdings.get(trade.symbol, 0) <= 0:
                    current_holdings.pop(trade.symbol, None)
            trade_index += 1

        # b. Calculate portfolio value at the end of the day
        portfolio_value_on_date = current_capital
        for symbol, quantity in current_holdings.items():
            if quantity > 0:
                # Find the most recent closing price on or before current_date
                price_lookup_date = current_date
                close_price = None
                # Search backwards for a valid price, max 1 year to prevent long loops
                for _ in range(366):
                    if symbol in all_historical_data and price_lookup_date in all_historical_data[symbol]:
                        close_price = all_historical_data[symbol][price_lookup_date]
                        break
                    price_lookup_date -= timedelta(days=1)
                    if price_lookup_date < start_date:
                        break

                if close_price is not None:
                    portfolio_value_on_date += quantity * close_price
                else:
                    logger.warning(
                        f"No historical price found for {symbol} on or before {current_date}. "
                        f"Cannot calculate its value in portfolio for this day."
                    )

        # c. Append daily performance point
        performance_history.append(
            schemas.PerformancePoint(
                timestamp=current_date, portfolio_value=portfolio_value_on_date
            )
        )
        current_date += timedelta(days=1)

    return performance_history


def calculate_simulation_metrics(
    simulation: models.Simulation,
    trades: List[models.Trade],
    current_prices: Dict[str, float],
    db: Session,
) -> schemas.SimulationStatus:
    """
    Calculates the current status, P&L, and performance history of a simulation.

    Args:
        simulation: The simulation database model.
        trades: A list of all trades for the simulation.
        current_prices: A dictionary mapping stock symbols to their current market price.
        db: The database session.

    Returns:
        A SimulationStatus schema object with the calculated metrics.
    """
    current_capital = simulation.initial_capital
    current_holdings: Dict[str, int] = {}

    # 1. Iterate through trades to determine current cash and holdings
    for trade in trades:
        if trade.action == 'BUY':
            current_capital -= trade.quantity * trade.price + trade.fee
            current_holdings[trade.symbol] = (
                current_holdings.get(trade.symbol, 0) + trade.quantity
            )
        elif trade.action == 'SELL':
            current_capital += trade.quantity * trade.price - trade.fee
            current_holdings[trade.symbol] = (
                current_holdings.get(trade.symbol, 0) - trade.quantity
            )
            if current_holdings.get(trade.symbol, 0) <= 0:
                current_holdings.pop(trade.symbol, None)

    # 2. Calculate the current market value of all holdings
    market_value_of_holdings = 0.0
    for symbol, quantity in current_holdings.items():
        if quantity > 0:
            price = current_prices.get(symbol)
            if price is not None:
                market_value_of_holdings += quantity * price
            else:
                logger.warning(
                    f"Current price for holding '{symbol}' not available. "
                    f"Assuming 0 value for current P&L calculation."
                )

    # 3. Calculate total portfolio value and P&L
    current_portfolio_value = current_capital + market_value_of_holdings
    total_pnl = current_portfolio_value - simulation.initial_capital

    # 4. Generate the performance history chart data
    performance_history = calculate_performance_history(db, simulation, trades)

    # 5. Return the complete simulation status
    return schemas.SimulationStatus(
        simulation_id=simulation.id,
        current_capital=current_portfolio_value,  # Represents total portfolio value
        pnl=total_pnl,
        performance_history=performance_history,
    )
