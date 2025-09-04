import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Defines application-wide configuration variables.

    These settings are loaded from environment variables or a .env file.
    Pydantic provides type validation for these settings.
    """

    # Project Settings
    PROJECT_NAME: str = "Stockast"
    API_V1_STR: str = "/api/v1"

    # Security Settings
    # This key is used for signing JWTs. It should be a long, random string.
    # Generate one with: openssl rand -hex 32
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    # Access token expiration in minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database Settings
    # The connection URI for the SQLAlchemy database.
    # Example for PostgreSQL: postgresql://user:password@host:port/dbname
    # Example for SQLite: sqlite:///./stockast.db
    SQLALCHEMY_DATABASE_URI: str

    # Google Cloud Vertex AI Settings (Optional)
    VERTEX_AI_PROJECT_ID: Optional[str] = None
    VERTEX_AI_LOCATION: Optional[str] = None

    class Config:
        """
        Pydantic model configuration.

        Specifies that settings should be loaded from a .env file and that
        environment variable names are case-sensitive.
        """
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'


# A singleton instance of the Settings class to be used throughout the application.
# This instance will automatically load configuration values from environment
# variables or the .env file as defined in the inner Config class.
settings = Settings()
