from pydantic import BaseModel

from domain.entities import PyObjectId
from domain.entities.user import UserEntity


class UserDetailResponse(UserEntity):
    model_config = {"from_attributes": True}


class FavoritePropertyResponse(UserDetailResponse):
    property_id: PyObjectId
    is_favorite: bool


class FavoritePropertyStatusResponse(BaseModel):
    property_id: PyObjectId
    is_favorite: bool
