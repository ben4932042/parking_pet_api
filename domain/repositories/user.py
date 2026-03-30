from abc import ABC, abstractmethod
from typing import Optional

from domain.entities import PyObjectId
from domain.entities.user import UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def basic_sign_in(self, name: str) -> UserEntity: ...
    @abstractmethod
    async def get_user_by_id(self, user_id: PyObjectId) -> Optional[UserEntity]: ...
    @abstractmethod
    async def update_user_profile(self, user_id: str, name: str) -> UserEntity: ...

    @abstractmethod
    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ) -> UserEntity: ...
