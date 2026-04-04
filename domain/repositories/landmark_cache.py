from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.landmark_cache import LandmarkCacheEntity


class ILandmarkCacheRepository(ABC):
    @abstractmethod
    async def get_by_key(self, cache_key: str) -> Optional[LandmarkCacheEntity]: ...

    @abstractmethod
    async def save(self, entry: LandmarkCacheEntity) -> LandmarkCacheEntity: ...
