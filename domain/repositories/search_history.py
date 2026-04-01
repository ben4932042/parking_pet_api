from abc import ABC, abstractmethod

from domain.entities.search_history import SearchHistoryEntity


class ISearchHistoryRepository(ABC):
    @abstractmethod
    async def create(self, history: SearchHistoryEntity) -> SearchHistoryEntity: ...

    @abstractmethod
    async def list_by_user_id(
        self,
        user_id: str,
        *,
        limit: int = 20,
    ) -> list[SearchHistoryEntity]: ...
