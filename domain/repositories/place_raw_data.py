from abc import ABC, abstractmethod

from domain.entities.enrichment import AnalysisSource


class IPlaceRawDataRepository(ABC):
    @abstractmethod
    async def create(self, source: AnalysisSource):
        ...
    @abstractmethod
    async def save(self, source: AnalysisSource):
        ...
    #
    # @abstractmethod
    # async def update_reviews(self, source: AnalysisSource):
    #     ...
