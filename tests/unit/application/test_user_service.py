import pytest

from application.user import UserService
from domain.repositories.user import IUserRepository


class UserRepoStub(IUserRepository):
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    async def register_basic_user(self, name: str, pet_name: str | None = None):
        self.calls.append(
            {"fn": "register_basic_user", "name": name, "pet_name": pet_name}
        )
        return self.user

    async def get_user_by_id(self, user_id: str):
        self.calls.append({"fn": "get_user_by_id", "user_id": user_id})
        return self.user

    async def register_apple_user(
        self,
        *,
        apple_user_identifier: str,
        name: str,
        pet_name: str | None = None,
        email: str | None = None,
    ):
        self.calls.append(
            {
                "fn": "register_apple_user",
                "apple_user_identifier": apple_user_identifier,
                "name": name,
                "pet_name": pet_name,
                "email": email,
            }
        )
        return self.user

    async def get_user_by_apple_user_identifier(self, apple_user_identifier: str):
        self.calls.append(
            {
                "fn": "get_user_by_apple_user_identifier",
                "apple_user_identifier": apple_user_identifier,
            }
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

    async def get_property_note(self, user_id: str, property_id: str):
        self.calls.append(
            {"fn": "get_property_note", "user_id": user_id, "property_id": property_id}
        )
        return None

    async def upsert_property_note(self, user_id: str, property_id: str, content: str):
        self.calls.append(
            {
                "fn": "upsert_property_note",
                "user_id": user_id,
                "property_id": property_id,
                "content": content,
            }
        )
        return None

    async def delete_property_note(self, user_id: str, property_id: str):
        self.calls.append(
            {
                "fn": "delete_property_note",
                "user_id": user_id,
                "property_id": property_id,
            }
        )
        return False

    async def list_property_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ):
        self.calls.append(
            {
                "fn": "list_property_notes",
                "user_id": user_id,
                "page": page,
                "size": size,
                "query": query,
            }
        )
        return [], 0

    async def record_recent_search(self, user_id: str, query: str, *, limit: int = 20):
        self.calls.append(
            {
                "fn": "record_recent_search",
                "user_id": user_id,
                "query": query,
                "limit": limit,
            }
        )
        return self.user

    async def delete_user(self, user_id: str):
        self.calls.append({"fn": "delete_user", "user_id": user_id})
        return True

    async def restore_user(self, user_id: str):
        self.calls.append({"fn": "restore_user", "user_id": user_id})
        return self.user

    async def start_auth_session(self, *, user_id: str, refresh_token_hash: str):
        self.calls.append(
            {
                "fn": "start_auth_session",
                "user_id": user_id,
                "refresh_token_hash": refresh_token_hash,
            }
        )
        return self.user

    async def rotate_refresh_token(self, *, user_id: str, refresh_token_hash: str):
        self.calls.append(
            {
                "fn": "rotate_refresh_token",
                "user_id": user_id,
                "refresh_token_hash": refresh_token_hash,
            }
        )
        return self.user

    async def revoke_auth_session(self, *, user_id: str):
        self.calls.append({"fn": "revoke_auth_session", "user_id": user_id})
        return self.user


@pytest.mark.asyncio
async def test_register_basic_user_delegates_to_repo(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben")
    repo = UserRepoStub(user=user)
    service = UserService(repo=repo)

    result = await service.register_basic_user(name="Ben", pet_name="Mochi")

    assert result == user
    assert repo.calls == [
        {"fn": "register_basic_user", "name": "Ben", "pet_name": "Mochi"}
    ]


@pytest.mark.asyncio
async def test_get_user_by_id_delegates_to_repo(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben")
    repo = UserRepoStub(user=user)
    service = UserService(repo=repo)

    result = await service.get_user_by_id("u1")

    assert result == user
    assert repo.calls == [{"fn": "get_user_by_id", "user_id": "u1"}]


@pytest.mark.asyncio
async def test_update_user_profile_delegates_to_repo(user_entity_factory):
    updated_user = user_entity_factory(
        identifier="u1", name="Ben Updated", pet_name="Mochi"
    )
    repo = UserRepoStub(user=updated_user)
    service = UserService(repo=repo)

    result = await service.update_user_profile(
        user_id="u1",
        name="Ben Updated",
        pet_name="Mochi",
    )

    assert result == updated_user
    assert repo.calls == [
        {
            "fn": "update_user_profile",
            "user_id": "u1",
            "name": "Ben Updated",
            "pet_name": "Mochi",
        }
    ]


@pytest.mark.asyncio
async def test_update_favorite_property_delegates_to_repo(user_entity_factory):
    user = user_entity_factory(
        identifier="u1", name="Ben", favorite_property_ids=["p1"]
    )
    repo = UserRepoStub(user=user)
    service = UserService(repo=repo)

    result = await service.update_favorite_property(
        user_id="u1", property_id="p1", is_favorite=True
    )

    assert result == user
    assert repo.calls == [
        {
            "fn": "update_favorite_property",
            "user_id": "u1",
            "property_id": "p1",
            "is_favorite": True,
        }
    ]


@pytest.mark.asyncio
async def test_record_recent_search_delegates_to_repo(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben")
    repo = UserRepoStub(user=user)
    service = UserService(repo=repo)

    result = await service.record_recent_search(
        user_id="u1", query="台北餐廳", limit=10
    )

    assert result == user
    assert repo.calls == [
        {
            "fn": "record_recent_search",
            "user_id": "u1",
            "query": "台北餐廳",
            "limit": 10,
        }
    ]


@pytest.mark.asyncio
async def test_delete_user_delegates_to_repo():
    repo = UserRepoStub()
    service = UserService(repo=repo)

    result = await service.delete_user("u1")

    assert result is True
    assert repo.calls == [{"fn": "delete_user", "user_id": "u1"}]
