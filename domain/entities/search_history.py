from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from domain.entities import PyObjectId
from domain.entities.search_feedback import SearchResponseType


class SearchHistoryPreference(BaseModel):
    key: str
    label: str

    @field_validator("key", "label")
    @classmethod
    def normalize_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Preference values cannot be empty.")
        return normalized


class SearchHistoryEntity(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    query: str = Field(min_length=1)
    response_type: SearchResponseType
    preferences: list[SearchHistoryPreference] = Field(default_factory=list)
    result_ids: list[str] = Field(default_factory=list)
    result_count: int = Field(default=0, ge=0)
    user_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    @field_validator("query", "user_id")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty.")
        return normalized

    @field_validator("result_ids")
    @classmethod
    def normalize_result_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]
