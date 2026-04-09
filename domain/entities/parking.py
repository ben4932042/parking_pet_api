from datetime import UTC, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from domain.entities.property import PointLocation


class NearbyParkingCandidate(BaseModel):
    place_id: str
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    primary_type: Optional[str] = None
    types: List[str] = Field(default_factory=list)


class ParkingEntity(BaseModel):
    id: str = Field(alias="_id")
    place_id: str
    name: str
    address: Optional[str] = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location: Optional[PointLocation] = None
    primary_type: Optional[str] = None
    types: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
    }

    @model_validator(mode="after")
    def generate_location(self) -> "ParkingEntity":
        self.location = PointLocation(coordinates=[self.longitude, self.latitude])
        return self

    @classmethod
    def from_candidate(cls, candidate: NearbyParkingCandidate) -> "ParkingEntity":
        return cls(
            _id=candidate.place_id,
            place_id=candidate.place_id,
            name=candidate.name,
            address=candidate.address,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            primary_type=candidate.primary_type,
            types=candidate.types,
        )
