from domain.entities.audit import ActorInfo
from domain.entities.search_feedback import (
    SearchFeedbackEntity,
    SearchFeedbackPreference,
    SearchResponseType,
)
from domain.repositories.search_feedback import ISearchFeedbackRepository


class SearchFeedbackService:
    def __init__(self, repo: ISearchFeedbackRepository):
        self.repo = repo

    async def create_feedback(
        self,
        query: str,
        response_type: SearchResponseType,
        reason: str,
        preferences: list[SearchFeedbackPreference],
        result_ids: list[str],
        actor: ActorInfo,
    ) -> SearchFeedbackEntity:
        feedback = SearchFeedbackEntity(
            query=query,
            response_type=response_type,
            reason=reason,
            preferences=preferences,
            result_ids=result_ids,
            user_id=actor.user_id or "",
            user_name=actor.name,
            source=actor.source,
        )
        return await self.repo.create(feedback)
