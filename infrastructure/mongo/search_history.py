from domain.entities.search_history import SearchHistoryEntity
from domain.repositories.search_history import ISearchHistoryRepository


class SearchHistoryRepository(ISearchHistoryRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def create(self, history: SearchHistoryEntity) -> SearchHistoryEntity:
        payload = history.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(payload)
        return history.model_copy(update={"id": str(result.inserted_id)})

    async def list_by_user_id(
        self,
        user_id: str,
        *,
        limit: int = 20,
    ) -> list[SearchHistoryEntity]:
        capped_limit = max(1, min(limit, 100))
        cursor = (
            self.collection.find({"user_id": user_id.strip()})
            .sort("created_at", -1)
            .limit(capped_limit)
        )
        docs = await cursor.to_list(length=capped_limit)
        return [SearchHistoryEntity(**doc) for doc in docs]
