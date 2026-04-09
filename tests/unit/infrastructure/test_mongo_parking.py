from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.entities.parking import ParkingEntity
from infrastructure.mongo.parking import ParkingRepository


@pytest.mark.asyncio
async def test_save_upserts_parking_by_place_id():
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.replace_one = AsyncMock()

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = ParkingRepository(client=ClientStub(), collection_name="parking")
    entity = ParkingEntity(
        _id="parking-1",
        place_id="parking-1",
        name="停車場 A",
        address="桃園市中壢區",
        latitude=25.01,
        longitude=121.21,
        primary_type="parking",
        types=["parking"],
    )

    saved = await repo.save(entity)

    assert saved.id == entity.id
    assert saved.created_at == entity.created_at
    assert saved.updated_at >= entity.updated_at
    assert collection.replace_one.await_args.args[0] == {"_id": "parking-1"}
    assert collection.replace_one.await_args.args[1]["location"] == {
        "type": "Point",
        "coordinates": [121.21, 25.01],
    }
    assert collection.replace_one.await_args.args[1]["created_at"] == entity.created_at
    assert "updated_at" in collection.replace_one.await_args.args[1]
    assert collection.replace_one.await_args.kwargs["upsert"] is True


@pytest.mark.asyncio
async def test_save_preserves_created_at_when_parking_already_exists():
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    previous_updated_at = datetime(2026, 1, 2, tzinfo=UTC)
    collection = MagicMock()
    collection.find_one = AsyncMock(
        return_value={
            "_id": "parking-1",
            "place_id": "parking-1",
            "name": "停車場 A",
            "address": "桃園市中壢區",
            "latitude": 25.01,
            "longitude": 121.21,
            "location": {"type": "Point", "coordinates": [121.21, 25.01]},
            "primary_type": "parking",
            "types": ["parking"],
            "created_at": created_at,
            "updated_at": previous_updated_at,
        }
    )
    collection.replace_one = AsyncMock()

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = ParkingRepository(client=ClientStub(), collection_name="parking")
    entity = ParkingEntity(
        _id="parking-1",
        place_id="parking-1",
        name="停車場 A2",
        address="桃園市中壢區",
        latitude=25.02,
        longitude=121.22,
        primary_type="parking",
        types=["parking"],
    )

    saved = await repo.save(entity)

    assert saved.created_at == created_at
    assert saved.updated_at > previous_updated_at
    assert collection.replace_one.await_args.args[1]["created_at"] == created_at
    assert collection.replace_one.await_args.args[1]["updated_at"] > previous_updated_at
