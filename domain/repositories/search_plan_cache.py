from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.search_plan_cache import SearchPlanCacheEntity


class ISearchPlanCacheRepository(ABC):
    @abstractmethod
    def get_by_key(self, cache_key: str) -> Optional[SearchPlanCacheEntity]: ...

    @abstractmethod
    def save(self, entry: SearchPlanCacheEntity) -> SearchPlanCacheEntity: ...

    @abstractmethod
    def touch(self, cache_key: str) -> Optional[SearchPlanCacheEntity]: ...
