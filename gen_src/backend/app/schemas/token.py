from typing import List, Optional

from pydantic import BaseModel


class Token(BaseModel):
    """
    Schema for the JWT access token returned upon successful login.
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Schema for the data payload encoded within the JWT.
    This typically maps to the claims within the token.
    """
    username: Optional[str] = None
    scopes: List[str] = []
