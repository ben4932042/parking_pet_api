from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity


class IPropertyRepository(ABC):
    @abstractmethod
    async def get_by_keyword(self, q: str, type: Optional[str], page: int, size: int) -> Tuple[List[PropertyEntity], int]:
        ...
    @abstractmethod
    async def get_nearby(self, lat: float, lng: float, radius: int, type: Optional[str], page: int, size: int) -> Tuple[List[PropertyEntity], int]:
        ...
    @abstractmethod
    async def get_property_by_id(self, property_id: PyObjectId) -> Optional[PropertyEntity]:
        ...
    @abstractmethod
    async def get_properties_by_ids(self, property_ids: List[PyObjectId]) -> List[PropertyEntity]:
        ...
    @abstractmethod
    async def toggle_favorite(self, user_id: str, property_id: PyObjectId, is_favorite: bool) -> bool:
        ...
    @abstractmethod
    async def create(self, new_property: PropertyEntity):
        ...
