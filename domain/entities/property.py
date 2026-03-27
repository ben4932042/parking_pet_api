from pydantic import BaseModel, Field, model_validator
from typing import List, Literal, Optional
from datetime import datetime, UTC
from datetime import datetime, timezone, timedelta

from domain.entities.enrichment import AIAnalysis


class PointLocation(BaseModel):
    type: Literal["Point"] = Field(default="Point")
    coordinates: List[float] = Field(..., description="[lng, lat]")


class TimePoint(BaseModel):
    day: int = Field(..., ge=0, le=6, description="星期幾 (0=週日, 6=週六)")
    hour: int = Field(..., ge=0, le=23, description="24小時制的時")
    minute: int = Field(..., ge=0, le=59, description="分")

    def to_total_minutes(self) -> int:
        return self.day * 1440 + self.hour * 60 + self.minute


class OpeningPeriod(BaseModel):
    open: TimePoint
    close: Optional[TimePoint] = None

    def to_segments(self) -> list[dict]:
        if self.open and not self.close:
            if self.open.day == 0 and self.open.hour == 0 and self.open.minute == 0:
                return [{"s": 0, "e": 10079}]
            else:
                s = self.open.day * 1440 + self.open.hour * 60 + self.open.minute
                return [{"s": s, "e": s + 1439}]

        if self.open and self.close:
            s_time = self.open.day * 1440 + self.open.hour * 60 + self.open.minute
            e_time = self.close.day * 1440 + self.close.hour * 60 + self.close.minute
            if e_time <= s_time:
                e_time += 10080
            return [{"s": s_time, "e": e_time}]

        return []


class OpSegment(BaseModel):
    s: int = Field(description="開始分鐘數")
    e: int = Field(description="結束分鐘數")


class PropertyEntity(BaseModel):
    id: str = Field(alias="_id")
    name: str = Field(description="Name of the property")
    place_id: str = Field(description="Google Maps Place ID")
    latitude: float = Field(description="Latitude of the property", ge=-90, le=90)
    longitude: float = Field(description="Longitude of the property", ge=-180, le=180)
    regular_opening_hours: List[OpeningPeriod]

    address: str = Field(description="Address of the property")
    primary_type: str
    ai_analysis: AIAnalysis

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # generated field
    op_segments: List[OpSegment] = Field(default_factory=list)
    location: Optional[PointLocation] = Field(
        default=None, description="Geographic location of the property"
    )
    rating: Optional[float] = Field(default=0.0, description="Rating of the property")
    is_open: Optional[bool] = Field(default=None, description="Whether the property is currently open, if None, means not analyzed yet.")


    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def generate_segments(self) -> "PropertyEntity":
        if not self.regular_opening_hours:
            return self
        try:
            new_segments = []
            for period in self.regular_opening_hours:
                raw_segments = period.to_segments()
                for seg in raw_segments:
                    new_segments.append(OpSegment(**seg))

            new_segments.sort(key=lambda x: x.s)
            self.op_segments = new_segments
            return self
        except Exception as e:
            print(f"Error generating op_segments: {e}")
            return self

    @model_validator(mode="after")
    def generate_location(self) -> "PropertyEntity":
        if not self.longitude or not self.latitude:
            return self

        self.location = PointLocation(coordinates=[self.longitude, self.latitude])
        return self
    @model_validator(mode="after")
    def generate_rating(self) -> "PropertyEntity":
        self.rating = self.ai_analysis.ai_rating
        return self

    @model_validator(mode="after")
    def is_currently_open(self) -> "PropertyEntity":
        if not self.op_segments:
            self.is_open = None
            return self

        tz_taiwan = timezone(timedelta(hours=8))
        now = datetime.now(tz_taiwan)


        day_of_week = (now.weekday() + 1) % 7
        current_minutes = (day_of_week * 1440) + (now.hour * 60) + now.minute

        for segment in self.op_segments:
            start = segment.s
            end = segment.e

            if start <= current_minutes <= end:
                self.is_open = True
                return self
        self.is_open = False
        return self


class PropertySummary(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    types: List[str]
    rating: float
    tags: List[str]
    ai_summary: str
