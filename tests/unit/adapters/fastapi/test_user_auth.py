from interface.api.dependencies.db import get_user_repository
from interface.api.dependencies.user import get_auth_token_service
from infrastructure.auth.tokens import AuthTokenService


class UserRepositoryStub:
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    async def get_user_by_id(self, user_id: str):
        self.calls.append({"fn": "get_user_by_id", "user_id": user_id})
        return self.user


def test_get_me_requires_authentication_header(client):
    response = client.get("/api/v1/user/me")

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_get_me_rejects_invalid_user_id(client, override_api_dep):
    repo = override_api_dep(get_user_repository, UserRepositoryStub(user=None))
    token_service = override_api_dep(
        get_auth_token_service,
        AuthTokenService(
            signing_key="test-signing-key",
            ttl_seconds=3600,
            issuer="test-suite",
        ),
    )
    token = token_service.issue_access_token(
        user_id="missing-user", source="basic", session_version=0
    )

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert data["detail"] == "Invalid authentication credentials"
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "missing-user"}]


def test_get_me_rejects_deleted_user(client, override_api_dep, user_entity_factory):
    repo = override_api_dep(
        get_user_repository,
        UserRepositoryStub(
            user=user_entity_factory(identifier="u1", name="Ben").model_copy(
                update={"is_deleted": True}
            )
        ),
    )
    token_service = override_api_dep(
        get_auth_token_service,
        AuthTokenService(
            signing_key="test-signing-key",
            ttl_seconds=3600,
            issuer="test-suite",
        ),
    )
    token = token_service.issue_access_token(
        user_id="u1", source="basic", session_version=0
    )

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert data["detail"] == "Invalid authentication credentials"
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "u1"}]


def test_get_me_accepts_valid_bearer_token_for_apple_user(
    client, override_api_dep, user_entity_factory
):
    repo = override_api_dep(
        get_user_repository,
        UserRepositoryStub(
            user=user_entity_factory(identifier="u1", name="Ben", source="apple")
        ),
    )
    token_service = override_api_dep(
        get_auth_token_service,
        AuthTokenService(
            signing_key="test-signing-key",
            ttl_seconds=3600,
            issuer="test-suite",
        ),
    )
    token = token_service.issue_access_token(
        user_id="u1", source="apple", session_version=0
    )

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "u1"}]


def test_get_me_accepts_valid_bearer_token_for_basic_user(
    client, override_api_dep, user_entity_factory
):
    repo = override_api_dep(
        get_user_repository,
        UserRepositoryStub(
            user=user_entity_factory(identifier="u2", name="Mochi", source="basic")
        ),
    )
    token_service = override_api_dep(
        get_auth_token_service,
        AuthTokenService(
            signing_key="test-signing-key",
            ttl_seconds=3600,
            issuer="test-suite",
        ),
    )
    token = token_service.issue_access_token(
        user_id="u2", source="basic", session_version=0
    )

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "u2"}]


def test_get_me_rejects_bearer_token_for_mismatched_user_source(
    client, override_api_dep, user_entity_factory
):
    repo = override_api_dep(
        get_user_repository,
        UserRepositoryStub(
            user=user_entity_factory(identifier="u1", name="Ben", source="basic")
        ),
    )
    token_service = override_api_dep(
        get_auth_token_service,
        AuthTokenService(
            signing_key="test-signing-key",
            ttl_seconds=3600,
            issuer="test-suite",
        ),
    )
    token = token_service.issue_access_token(
        user_id="u1", source="apple", session_version=0
    )

    response = client.get(
        "/api/v1/user/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "UNAUTHORIZED"
    assert data["detail"] == "Invalid authentication credentials"
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "u1"}]


def test_update_profile_requires_authentication_header(client):
    response = client.patch(
        "/api/v1/user/profile",
        json={"name": "Ben Updated", "pet_name": "Mochi"},
    )

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_get_profile_requires_authentication_header(client):
    response = client.get("/api/v1/user/profile")

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_get_favorite_properties_requires_authentication_header(client):
    response = client.get("/api/v1/user/favorite")

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_get_search_history_requires_authentication_header(client):
    response = client.get("/api/v1/user/search-history")

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_delete_user_requires_authentication_header(client):
    response = client.delete("/api/v1/user")

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"
