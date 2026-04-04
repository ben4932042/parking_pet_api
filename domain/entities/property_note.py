from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class PropertyNoteEntity(BaseModel):
    property_id: str
    content: str = Field(min_length=1, max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Note content cannot be empty.")
        return normalized
