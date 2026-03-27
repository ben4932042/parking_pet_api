from abc import ABC, abstractmethod

from domain.entities.property import PropertyEntity, PropertySearchResultEntity


class IEnrichmentProvider(ABC):
    @abstractmethod
    def create_property_by_name(
        self,
        property_name: str
    ) -> PropertyEntity:
        ...

    async def search_by_chat(self, query: str, size: int) -> PropertySearchResultEntity:
        ...