from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from infrastructure.mongo.user import UserRepository


@pytest.mark.asyncio
async def test_register_basic_user_persists_pet_name():
    collection = AsyncMock()
    collection.insert_one.return_value.inserted_id = "507f1f77bcf86cd799439011"

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.register_basic_user(name="Ben", pet_name="Mochi")

    assert user.id == "507f1f77bcf86cd799439011"
    assert user.name == "Ben"
    assert user.pet_name == "Mochi"
    assert user.source == "basic"
    assert user.favorite_property_ids == []
    assert user.recent_searches == []
    collection.insert_one.assert_awaited_once_with(
        {
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "basic",
            "favorite_property_ids": [],
            "recent_searches": [],
        }
    )


@pytest.mark.asyncio
async def test_register_apple_user_persists_binding_fields():
    collection = AsyncMock()
    collection.insert_one.return_value.inserted_id = "507f1f77bcf86cd799439012"

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.register_apple_user(
        apple_user_identifier="apple-sub-1",
        name="Ben",
        pet_name="Mochi",
        email="ben@example.com",
    )

    assert user.id == "507f1f77bcf86cd799439012"
    assert user.source == "apple"
    assert user.apple_user_identifier == "apple-sub-1"
    assert user.email == "ben@example.com"
    insert_doc = collection.insert_one.await_args.args[0]
    assert insert_doc["source"] == "apple"
    assert insert_doc["apple_user_identifier"] == "apple-sub-1"
    assert insert_doc["email"] == "ben@example.com"


@pytest.mark.asyncio
async def test_get_user_by_apple_user_identifier_returns_matching_user():
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439012",
        "name": "Ben",
        "pet_name": "Mochi",
        "email": "ben@example.com",
        "source": "apple",
        "apple_user_identifier": "apple-sub-1",
        "favorite_property_ids": [],
        "recent_searches": [],
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
    }

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.get_user_by_apple_user_identifier("apple-sub-1")

    assert user is not None
    assert user.apple_user_identifier == "apple-sub-1"
    collection.find_one.assert_awaited_once_with(
        {"apple_user_identifier": "apple-sub-1"}
    )


@pytest.mark.asyncio
async def test_record_recent_search_deduplicates_and_prepends_latest_entry():
    collection = AsyncMock()
    collection.find_one.side_effect = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "basic",
            "favorite_property_ids": [],
            "recent_searches": [
                {
                    "query": "台北咖啡廳",
                    "searched_at": datetime(2026, 1, 1, tzinfo=UTC),
                },
                {
                    "query": "寵物公園",
                    "searched_at": datetime(2025, 12, 31, tzinfo=UTC),
                },
            ],
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
        {
            "_id": "507f1f77bcf86cd799439011",
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "basic",
            "favorite_property_ids": [],
            "recent_searches": [
                {
                    "query": "台北咖啡廳",
                    "searched_at": datetime(2026, 1, 2, tzinfo=UTC),
                },
                {
                    "query": "寵物公園",
                    "searched_at": datetime(2025, 12, 31, tzinfo=UTC),
                },
            ],
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
        },
    ]

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.record_recent_search(
        "507f1f77bcf86cd799439011",
        "台北咖啡廳",
        limit=20,
    )

    assert [item.query for item in user.recent_searches] == ["台北咖啡廳", "寵物公園"]
    update_doc = collection.update_one.await_args.args[1]
    assert [item["query"] for item in update_doc["$set"]["recent_searches"]] == [
        "台北咖啡廳",
        "寵物公園",
    ]


@pytest.mark.asyncio
async def test_record_recent_search_respects_limit():
    collection = AsyncMock()
    collection.find_one.side_effect = [
        {
            "_id": "507f1f77bcf86cd799439011",
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "basic",
            "favorite_property_ids": [],
            "recent_searches": [
                {"query": "q1", "searched_at": datetime(2026, 1, 1, tzinfo=UTC)},
                {"query": "q2", "searched_at": datetime(2026, 1, 1, tzinfo=UTC)},
            ],
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
        },
        {
            "_id": "507f1f77bcf86cd799439011",
            "name": "Ben",
            "pet_name": "Mochi",
            "source": "basic",
            "favorite_property_ids": [],
            "recent_searches": [
                {"query": "q0", "searched_at": datetime(2026, 1, 2, tzinfo=UTC)},
                {"query": "q1", "searched_at": datetime(2026, 1, 1, tzinfo=UTC)},
            ],
            "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
        },
    ]

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.record_recent_search(
        "507f1f77bcf86cd799439011",
        "q0",
        limit=2,
    )

    assert [item.query for item in user.recent_searches] == ["q0", "q1"]


@pytest.mark.asyncio
async def test_update_user_profile_updates_name_and_pet_name():
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Ben Updated",
        "pet_name": "Mochi",
        "source": "basic",
        "favorite_property_ids": [],
        "recent_searches": [],
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
    }

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.update_user_profile(
        user_id="507f1f77bcf86cd799439011",
        name="Ben Updated",
        pet_name="Mochi",
    )

    assert user.name == "Ben Updated"
    assert user.pet_name == "Mochi"
    collection.update_one.assert_awaited_once_with(
        {"_id": pytest.importorskip("bson").ObjectId("507f1f77bcf86cd799439011")},
        {"$set": {"name": "Ben Updated", "pet_name": "Mochi"}},
    )
