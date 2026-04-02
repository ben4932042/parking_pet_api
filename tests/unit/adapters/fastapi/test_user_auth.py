from interface.api.dependencies.db import get_user_repository


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

    response = client.get("/api/v1/user/me", headers={"x-user-id": "missing-user"})

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Invalid authentication credentials"
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "missing-user"}]


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
