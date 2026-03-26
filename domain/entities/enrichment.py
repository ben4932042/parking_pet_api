from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class PointLocation(BaseModel):
    type: Literal["Point"]
    coordinates: List[float] = Field(
        ...,
        description="[lng, lat]"
    )


class Review(BaseModel):
    author: str
    rating: int
    text: str
    time: str


class AIAnalysis(BaseModel):
    suitable_for: List[str]
    pros: List[str]
    cons: List[str]
    signature_items: List[str]
    ai_summary: str


class EnrichmentPropertyEntity(BaseModel):
    search_name: str
    display_name: str
    place_id: str

    lat: float
    lng: float
    location: PointLocation

    address: str
    rating: float
    user_rating_count: int

    price_level: Optional[str] = None
    types: List[str]
    business_status: str

    reviews: List[Review] = []
    ai_analysis: Optional[AIAnalysis] = None