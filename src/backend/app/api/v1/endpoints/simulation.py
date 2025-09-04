import sys
import os
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from app.crud import crud_simulation
from app.models import user as models_user
from app.schemas import simulation as schemas_simulation
from app.core.security import get_current_user
from app.db.session import get_db
from app.services import trade_simulator

router = APIRouter(
    prefix="/simulation",
    tags=["simulation"],
)


@router.post(
    "/start",
    response_model=schemas_simulation.Simulation,
    status_code=status.HTTP_201_CREATED,
)
def start_simulation(
    simulation_in: schemas_simulation.SimulationCreate,
    db: Session = Depends(get_db),
    current_user: models_user.User = Depends(get_current_user),
) -> Any:
    """
    Starts a new trading simulation for the current user.

    A user can only have one active simulation at a time.
    """
    active_simulation = crud_simulation.get_active_by_owner(
        db=db, owner_id=current_user.id
    )
    if active_simulation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active simulation.",
        )

    simulation = crud_simulation.create_with_owner(
        db=db, obj_in=simulation_in, owner_id=current_user.id
    )
    return simulation


@router.get("/status", response_model=schemas_simulation.SimulationStatus)
def get_simulation_status(
    db: Session = Depends(get_db),
    current_user: models_user.User = Depends(get_current_user),
) -> Any:
    """
    Retrieves the status of the user's active simulation, including performance metrics.
    """
    active_simulation = crud_simulation.get_active_by_owner(
        db=db, owner_id=current_user.id
    )
    if not active_simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active simulation found for this user.",
        )

    trades = crud_simulation.get_trades_by_simulation_id(
        db=db, simulation_id=active_simulation.id
    )

    # Calculate performance metrics using the trade simulator service
    metrics = trade_simulator.calculate_simulation_metrics(
        simulation=active_simulation, trades=trades
    )

    # Construct the response object by combining ORM model attributes with calculated metrics.
    # Pydantic's response_model will handle the conversion.
    status_data = active_simulation.__dict__
    status_data.update(metrics)

    return status_data


@router.get("/history", response_model=List[schemas_simulation.TradeHistory])
def get_simulation_history(
    db: Session = Depends(get_db),
    current_user: models_user.User = Depends(get_current_user),
) -> Any:
    """
    Retrieves the trade history for the user's active simulation.
    """
    active_simulation = crud_simulation.get_active_by_owner(
        db=db, owner_id=current_user.id
    )
    if not active_simulation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active simulation found for this user.",
        )

    trades = crud_simulation.get_trades_by_simulation_id(
        db=db, simulation_id=active_simulation.id
    )
    return trades
