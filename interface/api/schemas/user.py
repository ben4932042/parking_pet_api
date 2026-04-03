from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from domain.entities import PyObjectId

RequiredUserName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
OptionalPetName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class UserDetailResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    pet_name: str | None = None
    source: str
    favorite_property_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class UserAuthStatusResponse(BaseModel):
    authenticated: bool


class UserProfileResponse(BaseModel):
    name: str
    pet_name: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class UpdateUserProfileRequest(BaseModel):
    name: RequiredUserName
    pet_name: OptionalPetName | None = None


class RegisterBasicUserRequest(BaseModel):
    name: RequiredUserName
    pet_name: OptionalPetName | None = None


class AppleAuthResponse(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    pet_name: str | None = None
    favorite_property_ids: list[str]

    model_config = {"from_attributes": True, "populate_by_name": True}


class AppleAuthRequest(BaseModel):
    identity_token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    authorization_code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    user_identifier: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    name: RequiredUserName | None = None
    pet_name: OptionalPetName | None = None


class FavoritePropertyResponse(UserDetailResponse):
    property_id: PyObjectId
    is_favorite: bool


class FavoritePropertyStatusResponse(BaseModel):
    property_id: PyObjectId
    is_favorite: bool
