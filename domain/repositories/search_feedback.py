from abc import ABC, abstractmethod

from domain.entities.search_feedback import SearchFeedbackEntity, SearchResponseType


class ISearchFeedbackRepository(ABC):
    @abstractmethod
    async def create(self, feedback: SearchFeedbackEntity) -> SearchFeedbackEntity: ...

    @abstractmethod
    async def list_feedback(
        self,
        *,
        query_contains: str | None = None,
        reason_contains: str | None = None,
        response_type: SearchResponseType | None = None,
        user_id: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[SearchFeedbackEntity]: ...
