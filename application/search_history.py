from domain.entities.search_history import SearchHistoryEntity, SearchHistoryPreference
from domain.entities.search_feedback import SearchResponseType
from domain.repositories.search_history import ISearchHistoryRepository


class SearchHistoryService:
    def __init__(self, repo: ISearchHistoryRepository):
        self.repo = repo

    async def record_search(
        self,
        *,
        user_id: str,
        query: str,
        response_type: SearchResponseType,
        preferences: list[SearchHistoryPreference],
        result_ids: list[str],
        result_count: int,
    ) -> SearchHistoryEntity:
        history = SearchHistoryEntity(
            user_id=user_id,
            query=query,
            response_type=response_type,
            preferences=preferences,
            result_ids=result_ids,
            result_count=result_count,
        )
        return await self.repo.create(history)

    async def list_history(
        self,
        *,
        user_id: str,
        limit: int = 20,
    ) -> list[SearchHistoryEntity]:
        return await self.repo.list_by_user_id(user_id, limit=limit)
