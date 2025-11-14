import sys
from typing import Optional

# Pydantic v2 uses pydantic.ConfigDict whereas v1 uses pydantic.BaseModel.Config
# This is a forward-compatible way to handle it.
from pydantic import BaseModel, EmailStr

# Use ConfigDict for Pydantic v2, and a fallback for v1
try:
    from pydantic import ConfigDict
except ImportError:
    # Fallback for Pydantic v1
    class ConfigDict(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

# DESCRIPTION: This file defines the Pydantic schemas for user data validation and serialization.

# Schemas to Read/Return

class UserBase(BaseModel):
    """Base schema for a user, containing common attributes."""
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    vertex_ai_api_key: Optional[str] = None

class UserInDBBase(UserBase):
    """Base schema for a user as stored in the database, including ID."""
    id: int

    # Pydantic V2 configuration to allow mapping from ORM models
    # For Pydantic v1, this would be an inner class `Config` with `orm_mode = True`
    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    """
    Schema for a user object returned from the API.
    This schema is used for reading user data and excludes sensitive information
    like the password.
    """
    pass

class UserInDB(UserInDBBase):
    """
    Full user schema including the hashed password.
    This is used for internal operations, like reading the full user object
    from the database.
    """
    hashed_password: str

# Schemas to Create/Update

class UserCreate(UserBase):
    """Schema for creating a new user. Requires a password."""
    password: str

class UserUpdate(BaseModel):
    """Schema for updating a user's information. All fields are optional."""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    vertex_ai_api_key: Optional[str] = None
    password: Optional[str] = None
