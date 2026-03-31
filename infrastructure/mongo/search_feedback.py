from domain.entities.search_feedback import SearchFeedbackEntity
from domain.repositories.search_feedback import ISearchFeedbackRepository


class SearchFeedbackRepository(ISearchFeedbackRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def create(self, feedback: SearchFeedbackEntity) -> SearchFeedbackEntity:
        payload = feedback.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(payload)
        return feedback.model_copy(update={"id": str(result.inserted_id)})
