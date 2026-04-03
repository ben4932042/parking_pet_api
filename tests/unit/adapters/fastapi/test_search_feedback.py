from domain.entities.search_feedback import (
    SearchFeedbackEntity,
    SearchFeedbackPreference,
)
from interface.api.dependencies.db import get_user_repository
from interface.api.dependencies.user import get_auth_token_service
from interface.api.dependencies.search_feedback import get_search_feedback_service
from infrastructure.auth.tokens import AuthTokenService


class SearchFeedbackServiceStub:
    def __init__(self, feedback=None):
        self.feedback = feedback
        self.calls = []

    async def create_feedback(
        self,
        query: str,
        response_type: str,
        reason: str,
        preferences: list,
        result_ids: list[str],
        actor,
    ):
        self.calls.append(
            {
                "query": query,
                "response_type": response_type,
                "reason": reason,
                "preferences": preferences,
                "result_ids": result_ids,
                "actor": actor,
            }
        )
        return self.feedback


class UserRepositoryStub:
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    async def get_user_by_id(self, user_id: str):
        self.calls.append({"fn": "get_user_by_id", "user_id": user_id})
        return self.user


def _issue_auth_token(override_api_dep, *, user_id: str, source: str = "basic") -> str:
    token_service = override_api_dep(
        get_auth_token_service,
        AuthTokenService(
            signing_key="test-signing-key",
            ttl_seconds=3600,
            issuer="test-suite",
        ),
    )
    return token_service.issue_access_token(
        user_id=user_id,
        source=source,
        session_version=0,
    )


def test_create_search_feedback_requires_authentication_header(client):
    response = client.post(
        "/api/v1/search-feedback",
        json={"query": "桃園寵物友善餐廳", "response_type": "semantic_search"},
    )

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_create_search_feedback_persists_feedback_with_authenticated_user(
    client, override_api_dep, user_entity_factory
):
    feedback = SearchFeedbackEntity(
        _id="feedback-1",
        query="桃園寵物友善餐廳",
        response_type="semantic_search",
        reason="結果太少",
        preferences=[
            SearchFeedbackPreference(key="address_preference", label="桃園"),
        ],
        result_ids=["xxx", "yyy"],
        user_id="u1",
        user_name="Ben",
    )
    service = override_api_dep(
        get_search_feedback_service,
        SearchFeedbackServiceStub(feedback=feedback),
    )
    user_repo = override_api_dep(
        get_user_repository,
        UserRepositoryStub(user=user_entity_factory(identifier="u1", name="Ben")),
    )
    token = _issue_auth_token(override_api_dep, user_id="u1")

    response = client.post(
        "/api/v1/search-feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "桃園寵物友善餐廳",
            "response_type": "semantic_search",
            "reason": "結果太少",
            "preferences": [
                {"key": "address_preference", "label": "桃園"},
                {"key": "category_preference", "label": "restaurant"},
            ],
            "result_ids": ["xxx", "yyy"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "feedback_id": "feedback-1"}
    assert user_repo.calls == [{"fn": "get_user_by_id", "user_id": "u1"}]
    assert service.calls[0]["query"] == "桃園寵物友善餐廳"
    assert service.calls[0]["response_type"] == "semantic_search"
    assert service.calls[0]["reason"] == "結果太少"
    assert [item.key for item in service.calls[0]["preferences"]] == [
        "address_preference",
        "category_preference",
    ]
    assert service.calls[0]["result_ids"] == ["xxx", "yyy"]
    assert service.calls[0]["actor"].user_id == "u1"


def test_create_search_feedback_rejects_empty_query(
    client, override_api_dep, user_entity_factory
):
    override_api_dep(
        get_user_repository,
        UserRepositoryStub(user=user_entity_factory(identifier="u1", name="Ben")),
    )
    token = _issue_auth_token(override_api_dep, user_id="u1")

    response = client.post(
        "/api/v1/search-feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "   ", "response_type": "semantic_search"},
    )

    assert response.status_code == 422


def test_create_search_feedback_accepts_fallback_search_response_type(
    client, override_api_dep, user_entity_factory
):
    feedback = SearchFeedbackEntity(
        _id="feedback-2",
        query="台北餐廳",
        response_type="fallback_search",
        reason="結果太散",
        user_id="u1",
        user_name="Ben",
    )
    service = override_api_dep(
        get_search_feedback_service,
        SearchFeedbackServiceStub(feedback=feedback),
    )
    override_api_dep(
        get_user_repository,
        UserRepositoryStub(user=user_entity_factory(identifier="u1", name="Ben")),
    )
    token = _issue_auth_token(override_api_dep, user_id="u1")

    response = client.post(
        "/api/v1/search-feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "台北餐廳",
            "response_type": "fallback_search",
            "reason": "結果太散",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "feedback_id": "feedback-2"}
    assert service.calls[0]["response_type"] == "fallback_search"
