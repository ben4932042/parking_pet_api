from datetime import datetime, UTC
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict

from domain.entities import PyObjectId
from domain.entities.property_note import PropertyNoteEntity


class UserSearchRecord(BaseModel):
    query: str
    searched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserEntity(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    pet_name: str | None = None
    email: str | None = None
    source: Literal["apple", "guest"] = Field(default="guest")
    apple_user_identifier: str | None = None
    favorite_property_ids: list[str] = Field(default_factory=list)
    property_notes: list[PropertyNoteEntity] = Field(default_factory=list)
    recent_searches: list[UserSearchRecord] = Field(default_factory=list)
    session_version: int = 0
    refresh_token_hash: str | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
