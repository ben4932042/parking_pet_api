from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.property_note import PropertyNoteEntity


class IPropertyNoteRepository(ABC):
    @abstractmethod
    async def get_by_user_and_property(
        self, user_id: str, property_id: str
    ) -> Optional[PropertyNoteEntity]: ...

    @abstractmethod
    async def upsert(
        self, user_id: str, property_id: str, content: str
    ) -> PropertyNoteEntity: ...

    @abstractmethod
    async def delete(self, user_id: str, property_id: str) -> bool: ...

    @abstractmethod
    async def list_by_user(
        self, user_id: str, page: int, size: int, query: str | None = None
    ) -> tuple[list[PropertyNoteEntity], int]: ...

    @abstractmethod
    async def get_noted_property_ids(
        self, user_id: str, property_ids: list[str]
    ) -> set[str]: ...
