from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity
from domain.entities.user import UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def basic_sign_in(self, name: str) -> UserEntity:
        ...
    @abstractmethod
    async def get_user_by_id(self, user_id: PyObjectId) -> Optional[UserEntity]:
        ...
    @abstractmethod
    async def update_user_profile(self, user_id: str, name: str) -> UserEntity:
        ...