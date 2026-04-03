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
            "session_version": 0,
            "refresh_token_hash": None,
            "is_deleted": False,
            "deleted_at": None,
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
    assert user.is_deleted is False
    assert user.deleted_at is None
    insert_doc = collection.insert_one.await_args.args[0]
    assert insert_doc["source"] == "apple"
    assert insert_doc["apple_user_identifier"] == "apple-sub-1"
    assert insert_doc["email"] == "ben@example.com"
    assert insert_doc["session_version"] == 0
    assert insert_doc["refresh_token_hash"] is None
    assert insert_doc["is_deleted"] is False
    assert insert_doc["deleted_at"] is None


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
        "session_version": 0,
        "refresh_token_hash": None,
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
async def test_delete_user_removes_document():
    collection = AsyncMock()
    collection.update_one.return_value.matched_count = 1

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    deleted = await repo.delete_user("507f1f77bcf86cd799439011")

    assert deleted is True
    update_filter, update_doc = collection.update_one.await_args.args
    assert update_filter == {
        "_id": pytest.importorskip("bson").ObjectId("507f1f77bcf86cd799439011")
    }
    assert update_doc["$set"]["is_deleted"] is True
    assert update_doc["$set"]["deleted_at"] is not None
    assert update_doc["$set"]["updated_at"] is not None


@pytest.mark.asyncio
async def test_restore_user_clears_deleted_fields():
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Ben",
        "pet_name": "Mochi",
        "source": "apple",
        "apple_user_identifier": "apple-sub-1",
        "favorite_property_ids": [],
        "recent_searches": [],
        "session_version": 0,
        "refresh_token_hash": None,
        "is_deleted": False,
        "deleted_at": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
    }

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.restore_user("507f1f77bcf86cd799439011")

    assert user is not None
    assert user.is_deleted is False
    update_filter, update_doc = collection.update_one.await_args.args
    assert update_filter == {
        "_id": pytest.importorskip("bson").ObjectId("507f1f77bcf86cd799439011")
    }
    assert update_doc["$set"]["is_deleted"] is False
    assert update_doc["$set"]["deleted_at"] is None
    assert update_doc["$set"]["updated_at"] is not None


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
            "session_version": 0,
            "refresh_token_hash": None,
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
            "session_version": 0,
            "refresh_token_hash": None,
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
async def test_start_auth_session_increments_session_version_and_stores_hash():
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Ben",
        "source": "basic",
        "favorite_property_ids": [],
        "recent_searches": [],
        "session_version": 1,
        "refresh_token_hash": "hash-1",
        "is_deleted": False,
        "deleted_at": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
    }

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.start_auth_session(
        user_id="507f1f77bcf86cd799439011",
        refresh_token_hash="hash-1",
    )

    assert user is not None
    update_filter, update_doc = collection.update_one.await_args.args
    assert update_filter == {
        "_id": pytest.importorskip("bson").ObjectId("507f1f77bcf86cd799439011")
    }
    assert update_doc["$set"]["refresh_token_hash"] == "hash-1"
    assert update_doc["$inc"]["session_version"] == 1


@pytest.mark.asyncio
async def test_rotate_refresh_token_updates_hash_without_bumping_session_version():
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Ben",
        "source": "basic",
        "favorite_property_ids": [],
        "recent_searches": [],
        "session_version": 1,
        "refresh_token_hash": "hash-2",
        "is_deleted": False,
        "deleted_at": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
    }

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.rotate_refresh_token(
        user_id="507f1f77bcf86cd799439011",
        refresh_token_hash="hash-2",
    )

    assert user is not None
    update_doc = collection.update_one.await_args.args[1]
    assert update_doc["$set"]["refresh_token_hash"] == "hash-2"
    assert "$inc" not in update_doc


@pytest.mark.asyncio
async def test_revoke_auth_session_clears_hash_and_bumps_session_version():
    collection = AsyncMock()
    collection.find_one.return_value = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Ben",
        "source": "basic",
        "favorite_property_ids": [],
        "recent_searches": [],
        "session_version": 2,
        "refresh_token_hash": None,
        "is_deleted": False,
        "deleted_at": None,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 2, tzinfo=UTC),
    }

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = UserRepository(client=ClientStub(), collection_name="user")

    user = await repo.revoke_auth_session(user_id="507f1f77bcf86cd799439011")

    assert user is not None
    update_doc = collection.update_one.await_args.args[1]
    assert update_doc["$set"]["refresh_token_hash"] is None
    assert update_doc["$inc"]["session_version"] == 1


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
