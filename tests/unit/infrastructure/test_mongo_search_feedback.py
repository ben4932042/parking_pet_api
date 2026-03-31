from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from domain.entities.search_feedback import SearchFeedbackEntity
from infrastructure.mongo.search_feedback import SearchFeedbackRepository


@pytest.mark.asyncio
async def test_create_search_feedback_inserts_document_and_returns_saved_entity():
    collection = AsyncMock()
    collection.insert_one.return_value = SimpleNamespace(inserted_id="feedback-1")

    class ClientStub:
        def get_collection(self, collection_name: str):
            assert collection_name == "search_feedback"
            return collection

    repo = SearchFeedbackRepository(client=ClientStub(), collection_name="search_feedback")

    saved = await repo.create(
        SearchFeedbackEntity(
            query="桃園寵物友善餐廳",
            response_type="semantic_search",
            reason="結果太少",
            result_ids=["p1"],
            user_id="u1",
            user_name="Ben",
        )
    )

    assert saved.id == "feedback-1"
    collection.insert_one.assert_awaited_once()
