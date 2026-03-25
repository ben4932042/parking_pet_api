from typing import List, Optional

from pydantic import BaseModel, computed_field, Field


class PropertyNearbyRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius: int = Field(default=10000, description="Radius in meters")
    q: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)


class PropertySchema(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    types: List[str]
    rating: float
    tags: List[str]
    ai_summary: str


class PropertyListResponse(BaseModel):
    properties: List[PropertySchema]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.properties)
