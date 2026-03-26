from domain.entities import PyObjectId

from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class PointLocation(BaseModel):
    type: Literal["Point"] = Field(default="Point")
    coordinates: List[float] = Field(..., description="[lng, lat]")


class AIAnalysis(BaseModel):
    suitable_for: List[str]
    pros: List[str]
    cons: List[str]
    signature_items: List[str]
    ai_summary: str


class PropertyEntity(BaseModel):
    id: PyObjectId = Field(default=None, alias="_id")
    origin_search_name: Optional[str] = Field(
        default=None, description="The original search name used to find this property"
    )
    name: str = Field(description="Name of the property", alias="display_name")
    place_id: str = Field(description="Google Maps Place ID")
    latitude: float = Field(
        description="Latitude of the property", ge=-90, le=90, alias="lat"
    )
    longitude: float = Field(
        description="Longitude of the property", ge=-180, le=180, alias="lng"
    )
    rating: float = Field(
        description="Current rating of the property is getting from Google Maps API. In further development, it will be replaced by more dimensional rating system."
    )
    user_rating_count: int
    price_level: Optional[str] = None

    address: str = Field(description="Address of the property")
    types: str = Field(description="Types of the property")  # FIXME
    reviews: str = Field(default=None, description="Reviews of the property")
    ai_analysis: AIAnalysis

    location: PointLocation

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class PropertyDetailEntity(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    types: List[str]
    rating: float
    tags: List[str]
    ai_summary: str
