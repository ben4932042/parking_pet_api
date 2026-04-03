from abc import ABC, abstractmethod
from typing import Optional

from domain.entities import PyObjectId
from domain.entities.user import UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def register_basic_user(
        self, name: str, pet_name: str | None = None
    ) -> UserEntity: ...

    @abstractmethod
    async def register_apple_user(
        self,
        *,
        apple_user_identifier: str,
        name: str,
        pet_name: str | None = None,
        email: str | None = None,
    ) -> UserEntity: ...

    @abstractmethod
    async def get_user_by_id(self, user_id: PyObjectId) -> Optional[UserEntity]: ...

    @abstractmethod
    async def get_user_by_apple_user_identifier(
        self, apple_user_identifier: str
    ) -> Optional[UserEntity]: ...

    @abstractmethod
    async def update_user_profile(
        self,
        user_id: str,
        name: str,
        pet_name: str | None = None,
    ) -> UserEntity: ...

    @abstractmethod
    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ) -> UserEntity: ...

    @abstractmethod
    async def record_recent_search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = 20,
    ) -> UserEntity: ...

    @abstractmethod
    async def delete_user(self, user_id: PyObjectId) -> bool: ...

    @abstractmethod
    async def restore_user(self, user_id: PyObjectId) -> UserEntity | None: ...

    @abstractmethod
    async def start_auth_session(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
    ) -> UserEntity | None: ...

    @abstractmethod
    async def rotate_refresh_token(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
    ) -> UserEntity | None: ...

    @abstractmethod
    async def revoke_auth_session(self, *, user_id: str) -> UserEntity | None: ...
