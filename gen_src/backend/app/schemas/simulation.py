# backend/app/schemas/simulation.py

"""
This file defines the Pydantic schemas for trading simulations and individual trades.
"""

import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# Schemas for Trades

class TradeBase(BaseModel):
    """Base schema for a single trade, containing common attributes."""
    symbol: str
    action: str  # e.g., 'BUY' or 'SELL'
    quantity: int
    price: float
    fee: float = 0.0


class TradeCreate(TradeBase):
    """Schema for creating a new trade record. Inherits all fields from TradeBase."""
    pass


class TradeHistory(TradeBase):
    """Schema for a trade record returned from the database, including its ID and timestamp."""
    id: int
    simulation_id: int
    timestamp: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# Schemas for Simulations

class SimulationBase(BaseModel):
    """Base schema for a trading simulation, containing its initial capital."""
    initial_capital: float


class SimulationCreate(SimulationBase):
    """Schema for creating a new simulation. Inherits all fields from SimulationBase."""
    pass


class Simulation(SimulationBase):
    """Schema for a full simulation object, including its trades and metadata."""
    id: int
    owner_id: int
    start_date: datetime.datetime
    end_date: Optional[datetime.datetime] = None
    is_active: bool = True
    trades: List[TradeHistory] = []

    model_config = ConfigDict(from_attributes=True)


# Schemas for Simulation Performance

class PerformancePoint(BaseModel):
    """Schema for a single data point in the simulation's performance history."""
    timestamp: datetime.date
    portfolio_value: float

    model_config = ConfigDict(from_attributes=True)


class SimulationStatus(BaseModel):
    """Schema for the simulation status and performance metrics returned by the API."""
    simulation_id: int
    current_capital: float
    pnl: float
    performance_history: List[PerformancePoint]

    model_config = ConfigDict(from_attributes=True)
