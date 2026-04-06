from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity


class IPropertyRepository(ABC):
    @abstractmethod
    async def get_by_keyword(self, q: str) -> List[PropertyEntity]: ...
    @abstractmethod
    async def get_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        types: List[str],
        page: int,
        size: int,
    ) -> Tuple[List[PropertyEntity], int]: ...
    @abstractmethod
    async def get_in_bbox(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        types: List[str],
        query: Optional[str],
        limit: int,
    ) -> Tuple[List[PropertyEntity], int]: ...
    @abstractmethod
    async def get_property_by_id(
        self,
        property_id: PyObjectId,
        include_deleted: bool = False,
    ) -> Optional[PropertyEntity]: ...
    @abstractmethod
    async def get_properties_by_ids(
        self, property_ids: List[str]
    ) -> List[PropertyEntity]: ...
    @abstractmethod
    async def create(self, new_property: PropertyEntity): ...
    @abstractmethod
    async def find_by_query(
        self, query: dict, open_at_minutes: Optional[int] = None
    ) -> List[PropertyEntity]: ...
    @abstractmethod
    async def save(self, property_entity: PropertyEntity) -> PropertyEntity: ...
    @abstractmethod
    async def get_property_by_place_id(
        self,
        place_id: str,
        include_deleted: bool = False,
    ) -> Optional[PropertyEntity]: ...
