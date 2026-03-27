from typing import List, Optional

from pydantic import BaseModel, Field

from domain.entities.enrichment import AIAnalysis
from domain.entities.property import OpeningPeriod

class PropertyKeywordRequest(BaseModel):
    q: str
    type: Optional[str] = Field(default=None)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PropertyNearbyRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius: int = Field(default=10000, description="Radius in meters")
    types_str: Optional[str] = Field(default=None)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)



class PropertyOverviewResponse(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    rating: float
    is_open: Optional[bool]

class PropertySearchResponse(BaseModel):
    status: str
    original_tags: List[str] = Field(default_factory=list)
    active_tags: List[str] = Field(default_factory=list)
    results: List[PropertyOverviewResponse] = Field(default_factory=list)


class PropertyDetailSchema(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    types: List[str]
    rating: float
    tags: List[str]
    regular_opening_hours: List[OpeningPeriod]
    ai_analysis: AIAnalysis



class PropertyDetailResponse(PropertyDetailSchema):
    model_config = {"from_attributes": True}
