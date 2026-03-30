import pytest

from application.user import UserService
from domain.repositories.user import IUserRepository


class UserRepoStub(IUserRepository):
    def __init__(self, user=None):
        self.user = user
        self.calls = []

    async def basic_sign_in(self, name: str):
        self.calls.append({"fn": "basic_sign_in", "name": name})
        return self.user

    async def get_user_by_id(self, user_id: str):
        self.calls.append({"fn": "get_user_by_id", "user_id": user_id})
        return self.user

    async def update_user_profile(self, user_id: str, name: str):
        self.calls.append(
            {"fn": "update_user_profile", "user_id": user_id, "name": name}
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


@pytest.mark.asyncio
async def test_basic_sign_in_delegates_to_repo(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben")
    repo = UserRepoStub(user=user)
    service = UserService(repo=repo)

    result = await service.basic_sign_in(name="Ben")

    assert result == user
    assert repo.calls == [{"fn": "basic_sign_in", "name": "Ben"}]


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
    updated_user = user_entity_factory(identifier="u1", name="Ben Updated")
    repo = UserRepoStub(user=updated_user)
    service = UserService(repo=repo)

    result = await service.update_user_profile(user_id="u1", name="Ben Updated")

    assert result == updated_user
    assert repo.calls == [
        {"fn": "update_user_profile", "user_id": "u1", "name": "Ben Updated"}
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
