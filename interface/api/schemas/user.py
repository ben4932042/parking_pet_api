from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from domain.entities import PyObjectId

RequiredUserName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
OptionalPetName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class UserDetailResponse(BaseModel):
    id: PyObjectId = Field(alias="_id", description="User id.")
    name: str
    pet_name: str | None = None
    source: str
    favorite_property_ids: list[str] = Field(
        description="Property ids favorited by the user."
    )
    created_at: datetime = Field(description="User creation timestamp.")
    updated_at: datetime = Field(description="User last update timestamp.")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "_id": "u1",
                "name": "Ben",
                "pet_name": "Mochi",
                "source": "apple",
                "favorite_property_ids": ["p1"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-02T00:00:00Z",
            }
        },
    }


class UserAuthStatusResponse(BaseModel):
    authenticated: bool = Field(
        description="Whether the provided bearer token maps to an active user session."
    )

    model_config = {"json_schema_extra": {"example": {"authenticated": True}}}


class UserProfileResponse(BaseModel):
    name: str = Field(description="Display name used in the app.")
    pet_name: str | None = Field(default=None, description="Optional pet name.")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {"example": {"name": "Ben", "pet_name": "Mochi"}},
    }


class UpdateUserProfileRequest(BaseModel):
    name: RequiredUserName = Field(description="Updated user display name.")
    pet_name: OptionalPetName | None = Field(
        default=None,
        description="Updated pet name. Omit or send null to clear it.",
    )

    model_config = {
        "json_schema_extra": {"example": {"name": "Ben Updated", "pet_name": "Mochi"}}
    }


class GuestAuthRequest(BaseModel):
    name: RequiredUserName = Field(description="Display name for a guest account.")
    pet_name: OptionalPetName | None = Field(
        default=None,
        description="Optional pet name saved on the user profile.",
    )

    model_config = {
        "json_schema_extra": {"example": {"name": "Ben", "pet_name": "Mochi"}}
    }


class UserAuthSessionResponse(BaseModel):
    access_token: str = Field(
        description="Short-lived bearer token for authenticated API requests."
    )
    refresh_token: str = Field(
        description="Refresh token used to obtain a new access token."
    )
    token_type: str = Field(default="Bearer", description="Authorization scheme.")
    user: UserDetailResponse = Field(
        description="Current user snapshot associated with the issued session."
    )

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "access_token": "access-token-value",
                "refresh_token": "refresh-token-value",
                "token_type": "Bearer",
                "user": {
                    "_id": "u1",
                    "name": "Ben",
                    "pet_name": "Mochi",
                    "source": "apple",
                    "favorite_property_ids": ["p1"],
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": "2026-01-02T00:00:00Z",
                },
            }
        },
    }


class AppleAuthRequest(BaseModel):
    identity_token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Apple identity token returned by Sign in with Apple.")
    authorization_code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Apple authorization code returned by Sign in with Apple.")
    user_identifier: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(
        description="Stable Apple user identifier from the client credential payload."
    )
    email: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = Field(
        default=None,
        description="Optional email returned by Apple, usually only on first consent.",
    )
    name: RequiredUserName | None = Field(
        default=None,
        description="Optional display name from the Apple consent flow. Required when creating a new user.",
    )
    pet_name: OptionalPetName | None = Field(
        default=None,
        description="Optional pet name to save when creating a new user.",
    )

    @field_validator("email", "name", "pet_name", mode="before")
    @classmethod
    def empty_optional_strings_to_none(cls, value: str | None):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "identity_token": "apple-identity-token",
                "authorization_code": "apple-authorization-code",
                "user_identifier": "apple-user-identifier",
                "email": "ben@example.com",
                "name": "Ben",
                "pet_name": "Mochi",
            }
        }
    }


class AppleLinkRequest(BaseModel):
    identity_token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Apple identity token returned by Sign in with Apple.")
    authorization_code: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Apple authorization code returned by Sign in with Apple.")
    user_identifier: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(
        description="Stable Apple user identifier from the client credential payload."
    )
    email: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = Field(
        default=None,
        description="Optional email returned by Apple, usually only on first consent.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def empty_optional_email_to_none(cls, value: str | None):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = {
        "json_schema_extra": {
            "example": {
                "identity_token": "apple-identity-token",
                "authorization_code": "apple-authorization-code",
                "user_identifier": "apple-user-identifier",
                "email": "ben@example.com",
            }
        }
    }


class FavoritePropertyResponse(UserDetailResponse):
    property_id: PyObjectId
    is_favorite: bool


class FavoritePropertyStatusResponse(BaseModel):
    property_id: PyObjectId = Field(description="Property id being checked.")
    is_favorite: bool = Field(description="Whether the property is favorited.")

    model_config = {
        "json_schema_extra": {"example": {"property_id": "p1", "is_favorite": True}}
    }


class UserDeleteResponse(BaseModel):
    user_id: PyObjectId = Field(description="Soft-deleted user id.")
    deleted: bool = Field(description="Whether the soft-delete operation succeeded.")

    model_config = {
        "json_schema_extra": {"example": {"user_id": "u1", "deleted": True}}
    }


class RefreshTokenRequest(BaseModel):
    refresh_token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Refresh token issued by a previous login or refresh call.")

    model_config = {
        "json_schema_extra": {"example": {"refresh_token": "refresh-token-value"}}
    }


class LogoutResponse(BaseModel):
    revoked: bool = Field(
        description="Whether the current auth session was successfully revoked."
    )
    model_config = {"json_schema_extra": {"example": {"revoked": True}}}
