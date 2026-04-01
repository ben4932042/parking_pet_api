import pytest

from application.search_history import SearchHistoryService
from domain.entities.search_history import SearchHistoryPreference
from domain.repositories.search_history import ISearchHistoryRepository


class InMemorySearchHistoryRepository(ISearchHistoryRepository):
    def __init__(self):
        self.items = []

    async def create(self, history):
        saved = history.model_copy(update={"id": "history-1"})
        self.items.append(saved)
        return saved

    async def list_by_user_id(self, user_id: str, *, limit: int = 20):
        return [item for item in self.items if item.user_id == user_id][:limit]


@pytest.mark.asyncio
async def test_record_search_persists_normalized_payload():
    repo = InMemorySearchHistoryRepository()
    service = SearchHistoryService(repo=repo)

    saved = await service.record_search(
        user_id=" u1 ",
        query=" 桃園寵物友善餐廳 ",
        response_type="semantic_search",
        preferences=[
            SearchHistoryPreference(key="address_preference", label="桃園"),
            SearchHistoryPreference(key="category_preference", label="restaurant"),
        ],
        result_ids=["p1", " p2 ", ""],
        result_count=2,
    )

    assert saved.id == "history-1"
    assert saved.user_id == "u1"
    assert saved.query == "桃園寵物友善餐廳"
    assert saved.result_ids == ["p1", "p2"]
    assert saved.result_count == 2
    assert repo.items[0].preferences[0].key == "address_preference"


@pytest.mark.asyncio
async def test_list_history_delegates_to_repo():
    repo = InMemorySearchHistoryRepository()
    service = SearchHistoryService(repo=repo)
    await service.record_search(
        user_id="u1",
        query="咖啡廳",
        response_type="keyword_search",
        preferences=[],
        result_ids=["p1"],
        result_count=1,
    )
    await service.record_search(
        user_id="u2",
        query="公園",
        response_type="semantic_search",
        preferences=[],
        result_ids=["p2"],
        result_count=1,
    )

    items = await service.list_history(user_id="u1", limit=10)

    assert len(items) == 1
    assert items[0].query == "咖啡廳"
