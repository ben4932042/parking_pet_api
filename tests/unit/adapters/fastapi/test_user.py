import logging
from datetime import datetime, timezone

from application.dto.property import PropertyOverviewDto
from application.auth_session import AuthSession
from domain.entities.property_note import PropertyNoteEntity
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_apple_auth_service,
    get_auth_session_service,
    get_current_user,
    get_user_service,
)


class UserServiceStub:
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    async def register_guest_user(self, name: str, pet_name: str | None = None):
        self.calls.append(
            {"fn": "register_guest_user", "name": name, "pet_name": pet_name}
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

    async def delete_user(self, user_id: str):
        self.calls.append({"fn": "delete_user", "user_id": user_id})
        return True


class FavoritePropertyServiceStub:
    def __init__(self, properties=None):
        self.properties = properties or []
        self.calls = []

    async def get_overviews_by_ids(
        self, property_ids, current_user=None, note_first=False
    ):
        self.calls.append({"fn": "get_overviews_by_ids", "property_ids": property_ids})
        noted_property_ids = (
            {note.property_id for note in current_user.property_notes}
            if current_user is not None
            else set()
        )
        favorite_property_ids = (
            set(current_user.favorite_property_ids)
            if current_user is not None
            else set()
        )
        items = [
            PropertyOverviewDto(
                id=item.id,
                name=item.name,
                address=item.address,
                latitude=item.latitude,
                longitude=item.longitude,
                category=item.category,
                types=item.types,
                rating=item.rating,
                is_open=item.is_open,
                has_note=item.id in noted_property_ids,
                is_favorite=item.id in favorite_property_ids,
            )
            for item in self.properties
        ]
        if note_first:
            items.sort(key=lambda item: not item.has_note)
        return items


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

    async def link_guest_user(
        self,
        *,
        current_user,
        identity_token: str,
        authorization_code: str,
        user_identifier: str,
        email: str | None = None,
    ):
        self.calls.append(
            {
                "current_user_id": str(current_user.id),
                "identity_token": identity_token,
                "authorization_code": authorization_code,
                "user_identifier": user_identifier,
                "email": email,
            }
        )
        if self.error is not None:
            raise self.error
        return self.user


class AuthSessionServiceStub:
    def __init__(
        self,
        *,
        access_token: str = "apple-access-token",
        refresh_token: str = "apple-refresh-token",
        user=None,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user = user
        self.calls = []

    async def start_session(self, *, user):
        self.calls.append(
            {"fn": "start_session", "user_id": str(user.id), "source": user.source}
        )
        return AuthSession(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            user=user,
        )

    async def refresh_session(self, *, refresh_token: str):
        self.calls.append({"fn": "refresh_session", "refresh_token": refresh_token})
        return AuthSession(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            user=self.user,
        )

    async def logout(self, *, user_id: str):
        self.calls.append({"fn": "logout", "user_id": user_id})
        return None


def test_guest_auth_returns_user_detail(
    client, override_api_dep, user_entity_factory, caplog
):
    user = user_entity_factory(identifier="u1", name="Ben", pet_name="Mochi")
    service = override_api_dep(get_user_service, UserServiceStub(user=user))
    auth_session_service = override_api_dep(
        get_auth_session_service,
        AuthSessionServiceStub(
            access_token="guest-access-token",
            refresh_token="guest-refresh-token",
        ),
    )

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.post(
            "/api/v1/user/auth/guest",
            json={"name": "Ben", "pet_name": "Mochi"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "access_token": "guest-access-token",
        "refresh_token": "guest-refresh-token",
        "token_type": "Bearer",
        "user": {
            "_id": "u1",
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "guest",
            "favorite_property_ids": [],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    assert service.calls == [
        {"fn": "register_guest_user", "name": "Ben", "pet_name": "Mochi"}
    ]
    record = next(
        record for record in caplog.records if record.event == "auth_registered"
    )
    assert record.user_id == "u1"
    assert record.source == "guest"
    assert auth_session_service.calls == [
        {"fn": "start_session", "user_id": "u1", "source": "guest"}
    ]


def test_apple_auth_returns_existing_user(
    client, override_api_dep, user_entity_factory
):
    user = user_entity_factory(
        identifier="u1",
        name="Ben",
        pet_name="Mochi",
        source="apple",
        apple_user_identifier="apple-sub-1",
        favorite_property_ids=["p1"],
    )
    service = override_api_dep(get_apple_auth_service, AppleAuthServiceStub(user=user))
    auth_session_service = override_api_dep(
        get_auth_session_service,
        AuthSessionServiceStub(),
    )

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
        "access_token": "apple-access-token",
        "refresh_token": "apple-refresh-token",
        "token_type": "Bearer",
        "user": {
            "_id": "u1",
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "apple",
            "favorite_property_ids": ["p1"],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
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
    assert auth_session_service.calls == [
        {"fn": "start_session", "user_id": "u1", "source": "apple"}
    ]


def test_apple_link_upgrades_guest_user(client, override_api_dep, user_entity_factory):
    current_user = user_entity_factory(identifier="u1", name="Ben", source="guest")
    linked_user = current_user.model_copy(
        update={
            "source": "apple",
            "email": "ben@example.com",
            "apple_user_identifier": "apple-sub-1",
        }
    )
    service = override_api_dep(
        get_apple_auth_service, AppleAuthServiceStub(user=linked_user)
    )
    override_api_dep(get_current_user, current_user)
    auth_session_service = override_api_dep(
        get_auth_session_service,
        AuthSessionServiceStub(),
    )

    response = client.post(
        "/api/v1/user/auth/apple/link",
        json={
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
            "email": "ben@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["source"] == "apple"
    assert service.calls == [
        {
            "current_user_id": "u1",
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
            "email": "ben@example.com",
        }
    ]
    assert auth_session_service.calls == [
        {"fn": "start_session", "user_id": "u1", "source": "apple"}
    ]


def test_apple_link_requires_guest_authentication(client):
    response = client.post(
        "/api/v1/user/auth/apple/link",
        json={
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
        },
    )

    assert response.status_code == 403


def test_refresh_user_session_returns_rotated_tokens(
    client, override_api_dep, user_entity_factory
):
    user = user_entity_factory(identifier="u1", name="Ben", source="guest")
    auth_session_service = override_api_dep(
        get_auth_session_service,
        AuthSessionServiceStub(
            access_token="rotated-access-token",
            refresh_token="rotated-refresh-token",
            user=user,
        ),
    )

    response = client.post(
        "/api/v1/user/auth/refresh",
        json={"refresh_token": "old-refresh-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "rotated-access-token",
        "refresh_token": "rotated-refresh-token",
        "token_type": "Bearer",
        "user": {
            "_id": "u1",
            "name": "Ben",
            "pet_name": None,
            "source": "guest",
            "favorite_property_ids": [],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    assert auth_session_service.calls == [
        {"fn": "refresh_session", "refresh_token": "old-refresh-token"}
    ]


def test_logout_user_revokes_current_session(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben", source="guest")
    override_api_dep(get_current_user, current_user)
    auth_session_service = override_api_dep(
        get_auth_session_service,
        AuthSessionServiceStub(user=current_user),
    )

    response = client.post("/api/v1/user/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"revoked": True}
    assert auth_session_service.calls == [{"fn": "logout", "user_id": "u1"}]


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


def test_apple_auth_allows_blank_optional_profile_fields_for_existing_user(
    client, override_api_dep, user_entity_factory
):
    user = user_entity_factory(
        identifier="u1",
        name="Ben",
        pet_name=None,
        source="apple",
        apple_user_identifier="apple-sub-1",
        favorite_property_ids=["p1"],
    )
    service = override_api_dep(get_apple_auth_service, AppleAuthServiceStub(user=user))
    auth_session_service = override_api_dep(
        get_auth_session_service,
        AuthSessionServiceStub(),
    )

    response = client.post(
        "/api/v1/user/auth/apple",
        json={
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
            "email": "",
            "name": "",
            "pet_name": "   ",
        },
    )

    assert response.status_code == 200
    assert service.calls == [
        {
            "identity_token": "token",
            "authorization_code": "code",
            "user_identifier": "apple-user-1",
            "email": None,
            "name": None,
            "pet_name": None,
        }
    ]
    assert auth_session_service.calls == [
        {"fn": "start_session", "user_id": "u1", "source": "apple"}
    ]


def test_get_user_profile_returns_name_and_pet_name(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben", pet_name="Mochi")
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/profile")

    assert response.status_code == 200
    data = response.json()
    assert data == {"name": "Ben", "pet_name": "Mochi"}


def test_update_user_profile_rejects_post_method(
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


def test_guest_auth_rejects_blank_name(client, override_api_dep):
    override_api_dep(get_user_service, UserServiceStub())

    response = client.post(
        "/api/v1/user/auth/guest",
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


def test_delete_current_user_returns_deleted_status(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    service = override_api_dep(get_user_service, UserServiceStub())
    override_api_dep(get_current_user, current_user)

    response = client.delete("/api/v1/user")

    assert response.status_code == 200
    assert response.json() == {"user_id": "u1", "deleted": True}
    assert service.calls == [{"fn": "delete_user", "user_id": "u1"}]


def test_update_user_favorite_property_returns_status(
    client, override_api_dep, user_entity_factory, caplog
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    updated_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1"]
    )
    service = override_api_dep(get_user_service, UserServiceStub(user=updated_user))
    override_api_dep(get_current_user, current_user)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.put(
            "/api/v1/user/favorite/p1", params={"is_favorite": "true"}
        )

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
    record = next(
        record for record in caplog.records if record.event == "user_favorite_added"
    )
    assert record.user_id == "u1"
    assert record.resource == {"type": "property", "id": "p1"}


def test_update_user_favorite_property_can_remove_favorite(
    client, override_api_dep, user_entity_factory, caplog
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1"]
    )
    updated_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=[]
    )
    service = override_api_dep(get_user_service, UserServiceStub(user=updated_user))
    override_api_dep(get_current_user, current_user)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.put(
            "/api/v1/user/favorite/p1", params={"is_favorite": "false"}
        )

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
    record = next(
        record for record in caplog.records if record.event == "user_favorite_removed"
    )
    assert record.user_id == "u1"
    assert record.resource == {"type": "property", "id": "p1"}


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
    caplog,
):
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        favorite_property_ids=["p1", "p2"],
        property_notes=[
            PropertyNoteEntity(
                property_id="p1",
                content="saved",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
    )
    properties = [
        property_entity_factory(identifier="p1", name="Cafe 1"),
        property_entity_factory(identifier="p2", name="Cafe 2"),
    ]
    service = override_api_dep(
        get_property_service, FavoritePropertyServiceStub(properties=properties)
    )
    override_api_dep(get_current_user, current_user)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.get("/api/v1/user/favorite")

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == ["p1", "p2"]
    assert [item["name"] for item in data] == ["Cafe 1", "Cafe 2"]
    assert [item["has_note"] for item in data] == [True, False]
    assert [item["is_favorite"] for item in data] == [True, True]
    assert service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": ["p1", "p2"]}
    ]
    record = next(
        record
        for record in caplog.records
        if record.event == "user_favorite_list_viewed"
    )
    assert record.user_id == "u1"
    assert record.favorite_count == 2


def test_get_user_favorite_properties_sorts_noted_items_first(
    client,
    override_api_dep,
    user_entity_factory,
    property_entity_factory,
):
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        favorite_property_ids=["p2", "p1"],
        property_notes=[
            PropertyNoteEntity(
                property_id="p1",
                content="saved",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
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
    assert [item["is_favorite"] for item in data] == [True, True]
    assert service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": ["p2", "p1"]}
    ]


def test_get_user_favorite_properties_returns_empty_list(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=[]
    )
    service = override_api_dep(
        get_property_service,
        FavoritePropertyServiceStub(properties=[]),
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/user/favorite")

    assert response.status_code == 200
    assert response.json() == []
    assert service.calls == [{"fn": "get_overviews_by_ids", "property_ids": []}]


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
