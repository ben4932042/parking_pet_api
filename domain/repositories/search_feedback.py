from abc import ABC, abstractmethod

from domain.entities.search_feedback import SearchFeedbackEntity


class ISearchFeedbackRepository(ABC):
    @abstractmethod
    async def create(self, feedback: SearchFeedbackEntity) -> SearchFeedbackEntity: ...
