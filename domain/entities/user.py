from datetime import datetime, UTC
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict

from domain.entities import PyObjectId


class UserEntity(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    source: Literal["apple", "basic"] = Field(default="basic")
    favorite_property_ids: list[PyObjectId] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
