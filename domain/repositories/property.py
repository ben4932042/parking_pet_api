from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity


class IPropertyRepository(ABC):
    @abstractmethod
    async def get_by_keyword(self, q: str, type: Optional[str], page: int, size: int) -> Tuple[List[PropertyEntity], int]:
        ...
    @abstractmethod
    async def get_nearby(self, lat: float, lng: float, radius: int, types: List[str], page: int, size: int) -> Tuple[List[PropertyEntity], int]:
        ...
    @abstractmethod
    async def get_property_by_id(self, property_id: PyObjectId) -> Optional[PropertyEntity]:
        ...
    @abstractmethod
    async def get_properties_by_ids(self, property_ids: List[str]) -> List[PropertyEntity]:
        ...
    @abstractmethod
    async def create(self, new_property: PropertyEntity):
        ...
