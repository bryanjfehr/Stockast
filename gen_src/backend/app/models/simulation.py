import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class Simulation(Base):
    """
    Represents a trading simulation session for a user.

    Each simulation has a starting capital, tracks its active status, and is associated
    with a specific user.
    """
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    initial_capital = Column(Float, nullable=False)
    start_date = Column(DateTime, default=func.now(), nullable=False)
    end_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner = relationship("User", back_populates="simulations")

    trades = relationship(
        "Trade", back_populates="simulation", cascade="all, delete-orphan"
    )


class Trade(Base):
    """
    Represents an individual trade (buy or sell) within a simulation.

    Each trade records the stock symbol, action, quantity, price, and timestamp,
    and is linked to a parent simulation.
    """
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(
        Integer, ForeignKey("simulations.id"), nullable=False, index=True
    )
    symbol = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # e.g., 'BUY' or 'SELL'
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0.0, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    simulation = relationship("Simulation", back_populates="trades")
