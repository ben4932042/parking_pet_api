from datetime import datetime, timezone

from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_apple_auth_service,
    get_current_user,
    get_user_service,
)


class UserServiceStub:
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    async def register_basic_user(self, name: str, pet_name: str | None = None):
        self.calls.append(
            {"fn": "register_basic_user", "name": name, "pet_name": pet_name}
        )
        return self.user

    async def update_user_profile(
        self,
        user_id: str,
        name: str,
        pet_name: str | None = None,
    ):
        self.calls.append(
            {
                "fn": "update_user_profile",
                "user_id": user_id,
                "name": name,
                "pet_name": pet_name,
            }
        )
        return self.user

    async def update_favorite_property(
        self, user_id: str, property_id: str, is_favorite: bool
    ):
        self.calls.append(
            {
                "fn": "update_favorite_property",
                "user_id": user_id,
                "property_id": property_id,
                "is_favorite": is_favorite,
            }
        )
        return self.user


class FavoritePropertyServiceStub:
    def __init__(self, properties=None, noted_property_ids=None):
        self.properties = properties or []
        self.noted_property_ids = (
            noted_property_ids if noted_property_ids is not None else {"p1"}
        )
        self.calls = []

    async def get_overviews_by_ids(self, property_ids):
        self.calls.append({"fn": "get_overviews_by_ids", "property_ids": property_ids})
        return self.properties

    async def get_noted_property_ids(self, user_id: str, property_ids: list[str]):
        self.calls.append(
            {
                "fn": "get_noted_property_ids",
                "user_id": user_id,
                "property_ids": property_ids,
            }
        )
        return self.noted_property_ids


class AppleAuthServiceStub:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error
        self.calls = []

    async def authenticate(
        self,
        *,
        identity_token: str,
        authorization_code: str,
        user_identifier: str,
        email: str | None = None,
        name: str | None = None,
        pet_name: str | None = None,
    ):
        self.calls.append(
            {
                "identity_token": identity_token,
                "authorization_code": authorization_code,
                "user_identifier": user_identifier,
                "email": email,
                "name": name,
                "pet_name": pet_name,
            }
        )
        if self.error is not None:
            raise self.error
        return self.user


def test_user_register_returns_user_detail(client, override_api_dep, user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben", pet_name="Mochi")
    service = override_api_dep(get_user_service, UserServiceStub(user=user))

    response = client.post(
        "/api/v1/user/register",
        json={"name": "Ben", "pet_name": "Mochi"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["_id"] == "u1"
    assert data["name"] == "Ben"
    assert data["pet_name"] == "Mochi"
    assert service.calls == [
        {"fn": "register_basic_user", "name": "Ben", "pet_name": "Mochi"}
    ]


def test_apple_auth_returns_existing_user(client, override_api_dep, user_entity_factory):
    user = user_entity_factory(
        identifier="u1",
        name="Ben",
        pet_name="Mochi",
        source="apple",
        apple_user_identifier="apple-sub-1",
        favorite_property_ids=["p1"],
    )
    service = override_api_dep(get_apple_auth_service, AppleAuthServiceStub(user=user))

    response = client.post(
        "/api/v1/user/auth/apple",
        json={
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
            "email": "ben@example.com",
            "name": "Ben",
            "pet_name": "Mochi",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "_id": "u1",
        "name": "Ben",
        "pet_name": "Mochi",
        "favorite_property_ids": ["p1"],
    }
    assert service.calls == [
        {
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
            "email": "ben@example.com",
            "name": "Ben",
            "pet_name": "Mochi",
        }
    ]


def test_apple_auth_rejects_blank_required_fields(client):
    response = client.post(
        "/api/v1/user/auth/apple",
        json={
            "identity_token": "   ",
            "authorization_code": "",
            "user_identifier": "   ",
            "email": None,
            "name": None,
            "pet_name": None,
        },
    )

    assert response.status_code == 422


def test_get_user_profile_returns_name_and_pet_name(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben", pet_name="Mochi")
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/profile")

    assert response.status_code == 200
    data = response.json()
    assert data == {"name": "Ben", "pet_name": "Mochi"}


def test_update_user_profile_returns_updated_profile(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    override_api_dep(get_current_user, current_user)

    response = client.post(
        "/api/v1/user/profile",
        json={"name": "Ben Updated", "pet_name": "Mochi"},
    )

    assert response.status_code == 405


def test_update_user_profile_returns_updated_profile(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    updated_user = user_entity_factory(
        identifier="u1", name="Ben Updated", pet_name="Mochi"
    )
    service = override_api_dep(get_user_service, UserServiceStub(user=updated_user))
    override_api_dep(get_current_user, current_user)

    response = client.patch(
        "/api/v1/user/profile",
        json={"name": "Ben Updated", "pet_name": "Mochi"},
    )
 
    assert response.status_code == 200
    data = response.json()
    assert data == {"name": "Ben Updated", "pet_name": "Mochi"}
    assert service.calls == [
        {
            "fn": "update_user_profile",
            "user_id": "u1",
            "name": "Ben Updated",
            "pet_name": "Mochi",
        }
    ]


def test_get_me_returns_authentication_status(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        recent_searches=[
            {
                "query": "台北餐廳",
                "searched_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            }
        ],
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/me")

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}


def test_register_rejects_blank_name(client, override_api_dep):
    override_api_dep(get_user_service, UserServiceStub())

    response = client.post(
        "/api/v1/user/register",
        json={"name": "   ", "pet_name": "Mochi"},
    )

    assert response.status_code == 422


def test_update_profile_rejects_blank_pet_name(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    override_api_dep(get_current_user, current_user)
    override_api_dep(get_user_service, UserServiceStub())

    response = client.patch(
        "/api/v1/user/profile",
        json={"name": "Ben", "pet_name": "   "},
    )

    assert response.status_code == 422


def test_update_user_favorite_property_returns_status(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    updated_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1"]
    )
    service = override_api_dep(get_user_service, UserServiceStub(user=updated_user))
    override_api_dep(get_current_user, current_user)

    response = client.put("/api/v1/user/favorite/p1", params={"is_favorite": "true"})

    assert response.status_code == 200
    data = response.json()
    assert data["_id"] == "u1"
    assert data["property_id"] == "p1"
    assert data["is_favorite"] is True
    assert service.calls == [
        {
            "fn": "update_favorite_property",
            "user_id": "u1",
            "property_id": "p1",
            "is_favorite": True,
        }
    ]


def test_update_user_favorite_property_can_remove_favorite(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1"]
    )
    updated_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=[]
    )
    service = override_api_dep(get_user_service, UserServiceStub(user=updated_user))
    override_api_dep(get_current_user, current_user)

    response = client.put("/api/v1/user/favorite/p1", params={"is_favorite": "false"})

    assert response.status_code == 200
    assert response.json()["is_favorite"] is False
    assert service.calls == [
        {
            "fn": "update_favorite_property",
            "user_id": "u1",
            "property_id": "p1",
            "is_favorite": False,
        }
    ]


def test_get_user_favorite_property_status_returns_boolean(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1"]
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/favorite/p1")

    assert response.status_code == 200
    assert response.json() == {"property_id": "p1", "is_favorite": True}


def test_get_user_favorite_property_status_returns_false_when_not_favorited(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=[]
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/favorite/p1")

    assert response.status_code == 200
    assert response.json() == {"property_id": "p1", "is_favorite": False}


def test_get_user_favorite_properties_returns_property_overviews(
    client,
    override_api_dep,
    user_entity_factory,
    property_entity_factory,
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1", "p2"]
    )
    properties = [
        property_entity_factory(identifier="p1", name="Cafe 1"),
        property_entity_factory(identifier="p2", name="Cafe 2"),
    ]
    service = override_api_dep(
        get_property_service, FavoritePropertyServiceStub(properties=properties)
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/favorite")

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == ["p1", "p2"]
    assert [item["name"] for item in data] == ["Cafe 1", "Cafe 2"]
    assert [item["has_note"] for item in data] == [True, False]
    assert service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": ["p1", "p2"]},
        {
            "fn": "get_noted_property_ids",
            "user_id": "u1",
            "property_ids": ["p1", "p2"],
        },
    ]


def test_get_user_favorite_properties_sorts_noted_items_first(
    client,
    override_api_dep,
    user_entity_factory,
    property_entity_factory,
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p2", "p1"]
    )
    properties = [
        property_entity_factory(identifier="p2", name="Cafe 2"),
        property_entity_factory(identifier="p1", name="Cafe 1"),
    ]
    service = override_api_dep(
        get_property_service, FavoritePropertyServiceStub(properties=properties)
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/favorite")

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == ["p1", "p2"]
    assert [item["has_note"] for item in data] == [True, False]
    assert service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": ["p2", "p1"]},
        {
            "fn": "get_noted_property_ids",
            "user_id": "u1",
            "property_ids": ["p2", "p1"],
        },
    ]


def test_get_user_favorite_properties_returns_empty_list(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=[]
    )
    service = override_api_dep(
        get_property_service,
        FavoritePropertyServiceStub(properties=[], noted_property_ids=set()),
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/favorite")

    assert response.status_code == 200
    assert response.json() == []
    assert service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": []},
        {"fn": "get_noted_property_ids", "user_id": "u1", "property_ids": []},
    ]


def test_get_user_search_history_returns_recent_items(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        recent_searches=[
            {
                "query": "台北咖啡廳",
                "searched_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
            }
        ],
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/search-history", params={"limit": 10})

    assert response.status_code == 200
    assert response.json() == [
        {
            "query": "台北咖啡廳",
            "searched_at": "2026-01-02T00:00:00Z",
        }
    ]
