from abc import ABC, abstractmethod

from domain.entities.property import PropertyEntity


class IEnrichmentProvider(ABC):
    @abstractmethod
    def create_property_by_name(
        self,
        property_name: str
    ) -> PropertyEntity:
        ...