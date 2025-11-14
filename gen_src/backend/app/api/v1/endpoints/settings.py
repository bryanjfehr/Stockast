# DESCRIPTION: This file defines the API endpoints for managing user settings.

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import get_current_user
from app.crud import crud_user
from app.db.session import get_db

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)


@router.put("/", response_model=schemas.Msg)
def update_settings(
    *, 
    db: Session = Depends(get_db),
    settings_in: schemas.SettingsUpdate,
    current_user: models.User = Depends(get_current_user),
) -> Any:
    """
    Updates settings for the current authenticated user.

    Args:
        db (Session): The database session dependency.
        settings_in (schemas.SettingsUpdate): The settings data to update.
        current_user (models.User): The current authenticated user dependency.

    Returns:
        dict: A message indicating successful update.
    """
    crud_user.user.update(db=db, db_obj=current_user, obj_in=settings_in)
    return {"message": "Settings updated successfully"}
