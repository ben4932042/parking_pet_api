from datetime import UTC, datetime
from typing import Optional

from pydantic import BaseModel, Field


class LandmarkCacheEntity(BaseModel):
    cache_key: str = Field(description="Normalized lookup key for the landmark query.")
    query_text: str = Field(
        description="Original normalized user-facing landmark text."
    )
    display_name: str = Field(
        description="Resolved display name returned by the provider."
    )
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def coordinates(self) -> tuple[float, float] | None:
        if self.longitude is None or self.latitude is None:
            return None
        return self.longitude, self.latitude
