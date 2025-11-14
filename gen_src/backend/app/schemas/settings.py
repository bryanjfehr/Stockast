from typing import Optional
from pydantic import BaseModel


class SettingsBase(BaseModel):
    """
    Defines the base fields for user settings, such as the Vertex AI API key.
    """
    vertex_ai_api_key: Optional[str] = None


class SettingsUpdate(SettingsBase):
    """
    Defines the schema for updating user settings.

    Inherits from SettingsBase. The optional nature of the fields in the base
    class makes it suitable for update operations where not all fields are provided.
    """
    pass


# Note: A 'Settings' or 'SettingsInDB' schema might be added later for reading
# data from the database, potentially including fields like 'user_id'.
# For now, the base and update schemas are sufficient as per the requirements.
