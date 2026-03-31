import pytest

from application.search_feedback import SearchFeedbackService
from domain.entities.audit import ActorInfo
from domain.entities.search_feedback import SearchFeedbackPreference
from domain.repositories.search_feedback import ISearchFeedbackRepository


class InMemorySearchFeedbackRepository(ISearchFeedbackRepository):
    def __init__(self):
        self.items = []

    async def create(self, feedback):
        saved = feedback.model_copy(update={"id": "feedback-1"})
        self.items.append(saved)
        return saved


@pytest.mark.asyncio
async def test_create_feedback_persists_actor_and_payload():
    repo = InMemorySearchFeedbackRepository()
    service = SearchFeedbackService(repo=repo)

    saved = await service.create_feedback(
        query=" 桃園寵物友善餐廳 ",
        response_type="semantic_search",
        reason=" 結果太少 ",
        preferences=[
            SearchFeedbackPreference(key="address_preference", label="桃園"),
            SearchFeedbackPreference(key="category_preference", label="restaurant"),
        ],
        result_ids=["p1", " p2 ", ""],
        actor=ActorInfo(user_id="u1", name="Ben", role="user", source="user"),
    )

    assert saved.id == "feedback-1"
    assert saved.query == "桃園寵物友善餐廳"
    assert saved.reason == "結果太少"
    assert saved.result_ids == ["p1", "p2"]
    assert saved.user_id == "u1"
    assert saved.user_name == "Ben"
    assert saved.source == "user"
    assert repo.items[0].preferences[0].key == "address_preference"
