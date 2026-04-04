from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.search_plan_cache import SearchPlanCacheEntity


class ISearchPlanCacheRepository(ABC):
    @abstractmethod
    async def get_by_key(self, cache_key: str) -> Optional[SearchPlanCacheEntity]: ...

    @abstractmethod
    async def save(self, entry: SearchPlanCacheEntity) -> SearchPlanCacheEntity: ...

    @abstractmethod
    async def touch(self, cache_key: str) -> Optional[SearchPlanCacheEntity]: ...
