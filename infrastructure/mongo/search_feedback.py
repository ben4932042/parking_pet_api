import re

from domain.entities.search_feedback import SearchFeedbackEntity
from domain.repositories.search_feedback import ISearchFeedbackRepository


class SearchFeedbackRepository(ISearchFeedbackRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def create(self, feedback: SearchFeedbackEntity) -> SearchFeedbackEntity:
        payload = feedback.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(payload)
        return feedback.model_copy(update={"id": str(result.inserted_id)})

    @staticmethod
    def _normalize_text_filter(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    async def list_feedback(
        self,
        *,
        query_contains: str | None = None,
        reason_contains: str | None = None,
        response_type: str | None = None,
        user_id: str | None = None,
        source: str | None = None,
        limit: int = 20,
    ) -> list[SearchFeedbackEntity]:
        filters: dict = {}

        normalized_query = self._normalize_text_filter(query_contains)
        if normalized_query:
            filters["query"] = {"$regex": re.escape(normalized_query), "$options": "i"}

        normalized_reason = self._normalize_text_filter(reason_contains)
        if normalized_reason:
            filters["reason"] = {
                "$regex": re.escape(normalized_reason),
                "$options": "i",
            }

        normalized_user_id = self._normalize_text_filter(user_id)
        if normalized_user_id:
            filters["user_id"] = normalized_user_id

        normalized_source = self._normalize_text_filter(source)
        if normalized_source:
            filters["source"] = normalized_source

        if response_type:
            filters["response_type"] = response_type

        capped_limit = max(1, min(limit, 200))
        cursor = self.collection.find(filters).sort("created_at", -1).limit(capped_limit)
        docs = await cursor.to_list(length=capped_limit)
        return [SearchFeedbackEntity(**doc) for doc in docs]
