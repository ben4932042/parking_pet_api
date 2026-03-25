from datetime import datetime, UTC
from typing import List

from pydantic import BaseModel, Field

from domain.entities import PyObjectId

from pydantic import BaseModel, Field
from typing import List


class PropertyEntity(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str = Field(description="Name of the property")
    address: str = Field(description="Address of the property")
    latitude: float = Field(description="Latitude of the property", ge=-90, le=90)
    longitude: float = Field(description="Longitude of the property", ge=-180, le=180)
    types: List[str] = Field(default_factory=List, description="Types of the property")
    rating: float = Field(
        description="Current rating of the property is getting from Google Maps API. In further development, it will be replaced by more dimensional rating system."
    )
    tags: List[str]
    ai_summary: str = Field(description="AI summary of the property")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class UserPreferenceEntity(PropertyEntity):
    user_id: str
    favorite_properties: List[PyObjectId]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
