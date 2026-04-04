from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class SearchPlanCacheEntity(BaseModel):
    cache_key: str = Field(min_length=1)
    query_text: str = Field(min_length=1)
    normalized_query: str = Field(min_length=1)
    version: str = Field(min_length=1)
    plan_payload: dict = Field(default_factory=dict)
    hit_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("cache_key", "query_text", "normalized_query", "version")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty.")
        return normalized
