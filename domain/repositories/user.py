from abc import ABC, abstractmethod
from typing import Optional

from domain.entities import PyObjectId
from domain.entities.property_note import PropertyNoteEntity
from domain.entities.user import UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def register_guest_user(
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
    async def link_guest_user_to_apple(
        self,
        *,
        user_id: str,
        apple_user_identifier: str,
        email: str | None = None,
    ) -> UserEntity | None: ...

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
    async def get_property_note(
        self, user_id: str, property_id: str
    ) -> PropertyNoteEntity | None: ...

    @abstractmethod
    async def upsert_property_note(
        self, user_id: str, property_id: str, content: str
    ) -> PropertyNoteEntity: ...

    @abstractmethod
    async def delete_property_note(self, user_id: str, property_id: str) -> bool: ...

    @abstractmethod
    async def list_property_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ) -> tuple[list[PropertyNoteEntity], int]: ...

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
