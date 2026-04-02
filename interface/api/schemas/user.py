from datetime import datetime

from pydantic import BaseModel, Field

from domain.entities import PyObjectId


class UserDetailResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    pet_name: str | None = None
    source: str
    favorite_property_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class FavoritePropertyResponse(UserDetailResponse):
    property_id: PyObjectId
    is_favorite: bool


class FavoritePropertyStatusResponse(BaseModel):
    property_id: PyObjectId
    is_favorite: bool
