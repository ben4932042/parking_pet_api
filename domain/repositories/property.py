from abc import ABC, abstractmethod
from typing import Optional, List

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity


class IPropertyRepository(ABC):
    @abstractmethod
    async def get_nearby(self, lat: float, lng: float, radius: int, q: Optional[str], type: Optional[str]) -> List[PropertyEntity]:
        ...
    @abstractmethod
    async def get_property_by_id(self, property_id: PyObjectId) -> Optional[PropertyEntity]:
        ...
    @abstractmethod
    async def toggle_favorite(self, user_id: str, property_id: PyObjectId, is_favorite: bool) -> bool:
        ...