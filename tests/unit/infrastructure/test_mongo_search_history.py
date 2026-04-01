from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from domain.entities.search_history import SearchHistoryEntity
from infrastructure.mongo.search_history import SearchHistoryRepository


@pytest.mark.asyncio
async def test_create_search_history_inserts_document_and_returns_saved_entity():
    collection = AsyncMock()
    collection.insert_one.return_value = SimpleNamespace(inserted_id="history-1")

    class ClientStub:
        def get_collection(self, collection_name: str):
            assert collection_name == "search_history"
            return collection

    repo = SearchHistoryRepository(client=ClientStub(), collection_name="search_history")

    saved = await repo.create(
        SearchHistoryEntity(
            query="桃園寵物友善餐廳",
            response_type="semantic_search",
            result_ids=["p1"],
            result_count=1,
            user_id="u1",
        )
    )

    assert saved.id == "history-1"
    collection.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_history_builds_expected_filters_and_returns_entities():
    docs = [
        {
            "_id": "history-2",
            "query": "想吃點心",
            "response_type": "semantic_search",
            "result_ids": ["p1"],
            "result_count": 1,
            "user_id": "u1",
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
            assert collection_name == "search_history"
            return collection

    repo = SearchHistoryRepository(client=ClientStub(), collection_name="search_history")

    items = await repo.list_by_user_id(" u1 ", limit=500)

    collection.find.assert_called_once_with({"user_id": "u1"})
    cursor.sort.assert_called_once_with("created_at", -1)
    cursor.limit.assert_called_once_with(100)
    cursor.to_list.assert_awaited_once_with(length=100)
    assert len(items) == 1
    assert items[0].id == "history-2"
    assert items[0].query == "想吃點心"
