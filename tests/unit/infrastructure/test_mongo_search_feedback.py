from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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


@pytest.mark.asyncio
async def test_list_feedback_builds_expected_filters_and_returns_entities():
    docs = [
        {
            "_id": "feedback-2",
            "query": "想吃點心",
            "response_type": "semantic_search",
            "reason": "結果不相關",
            "result_ids": ["p1"],
            "user_id": "u1",
            "user_name": "Ben",
            "source": "user",
        }
    ]

    cursor = Mock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)

    collection = Mock()
    collection.find.return_value = cursor

    class ClientStub:
        def get_collection(self, collection_name: str):
            assert collection_name == "search_feedback"
            return collection

    repo = SearchFeedbackRepository(client=ClientStub(), collection_name="search_feedback")

    items = await repo.list_feedback(
        query_contains=" 點心 ",
        reason_contains=" 不相關 ",
        response_type="semantic_search",
        user_id=" u1 ",
        source=" user ",
        limit=500,
    )

    collection.find.assert_called_once_with(
        {
            "query": {"$regex": "點心", "$options": "i"},
            "reason": {"$regex": "不相關", "$options": "i"},
            "response_type": "semantic_search",
            "user_id": "u1",
            "source": "user",
        }
    )
    cursor.sort.assert_called_once_with("created_at", -1)
    cursor.limit.assert_called_once_with(200)
    cursor.to_list.assert_awaited_once_with(length=200)
    assert len(items) == 1
    assert items[0].id == "feedback-2"
    assert items[0].query == "想吃點心"
