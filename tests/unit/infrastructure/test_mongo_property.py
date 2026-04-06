from infrastructure.mongo.property import PropertyRepository
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest


def test_build_variant_regex_matches_tai_and_tai_traditional():
    assert PropertyRepository._build_variant_regex("台北") == "[台臺]北"
    assert PropertyRepository._build_variant_regex("臺中市") == "[台臺]中市"


def test_normalize_regex_query_rewrites_nested_regex_strings():
    query = {
        "$and": [
            {"address": {"$regex": "台北", "$options": "i"}},
            {"$or": [{"name": {"$regex": "臺中店", "$options": "i"}}]},
        ]
    }

    normalized = PropertyRepository._normalize_regex_query(query)

    assert normalized == {
        "$and": [
            {"address": {"$regex": "[台臺]北", "$options": "i"}},
            {"$or": [{"name": {"$regex": "[台臺]中店", "$options": "i"}}]},
        ]
    }


def test_normalize_runtime_query_rewrites_is_open_to_op_segments():
    query = {
        "address": {"$regex": "台北", "$options": "i"},
        "is_open": True,
    }

    normalized = PropertyRepository._normalize_runtime_query(
        query, open_at_minutes=3720
    )

    assert normalized == {
        "address": {"$regex": "[台臺]北", "$options": "i"},
        "op_segments": {
            "$elemMatch": {
                "s": {"$lte": 3720},
                "e": {"$gte": 3720},
            }
        },
    }


@pytest.mark.asyncio
async def test_get_property_by_place_id_prefers_id_lookup_before_legacy_place_id():
    collection = AsyncMock()
    collection.find_one.side_effect = [
        None,
        {
            "_id": "place-1",
            "place_id": "place-1",
            "name": "Cafe 1",
            "latitude": 25.03,
            "longitude": 121.56,
            "regular_opening_hours": [],
            "address": "Test address",
            "primary_type": "cafe",
            "ai_analysis": {
                "venue_type": "pet-friendly cafe",
                "ai_summary": "summary",
                "pet_features": {
                    "rules": {
                        "leash_required": False,
                        "stroller_required": False,
                        "allow_on_floor": False,
                    },
                    "environment": {
                        "stairs": False,
                        "outdoor_seating": False,
                        "spacious": False,
                        "indoor_ac": True,
                        "off_leash_possible": False,
                        "pet_friendly_floor": True,
                        "has_shop_pet": False,
                    },
                    "services": {
                        "pet_menu": False,
                        "free_water": False,
                        "free_treats": False,
                        "pet_seating": False,
                    },
                },
                "highlights": [],
                "warnings": [],
                "rating": 4.0,
            },
        },
    ]

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = PropertyRepository(client=ClientStub(), collection_name="property_v2")

    entity = await repo.get_property_by_place_id("place-1")

    assert entity is not None
    assert entity.id == "place-1"
    assert collection.find_one.await_args_list[0].args[0] == {
        "$and": [{"is_deleted": {"$ne": True}}, {"_id": "place-1"}]
    }
    assert collection.find_one.await_args_list[1].args[0] == {
        "$and": [{"is_deleted": {"$ne": True}}, {"place_id": "place-1"}]
    }


@pytest.mark.asyncio
async def test_get_by_keyword_searches_aliases_in_lexical_query():
    find_cursor = MagicMock()
    find_cursor.limit.return_value = find_cursor
    find_cursor.max_time_ms.return_value = find_cursor
    find_cursor.to_list = AsyncMock(
        return_value=[
            {
                "_id": "place-1",
                "place_id": "place-1",
                "name": "青埔公七公園",
                "aliases": ["公七公園"],
                "latitude": 25.03,
                "longitude": 121.56,
                "regular_opening_hours": [],
                "address": "Test address",
                "primary_type": "park",
                "ai_analysis": {
                    "venue_type": "park",
                    "ai_summary": "summary",
                    "pet_features": {
                        "rules": {
                            "leash_required": False,
                            "stroller_required": False,
                            "allow_on_floor": False,
                        },
                        "environment": {
                            "stairs": False,
                            "outdoor_seating": False,
                            "spacious": False,
                            "indoor_ac": False,
                            "off_leash_possible": False,
                            "pet_friendly_floor": False,
                            "has_shop_pet": False,
                        },
                        "services": {
                            "pet_menu": False,
                            "free_water": False,
                            "free_treats": False,
                            "pet_seating": False,
                        },
                    },
                    "highlights": [],
                    "warnings": [],
                    "rating": 4.0,
                },
            }
        ]
    )
    collection = MagicMock()
    collection.find.return_value = find_cursor

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = PropertyRepository(client=ClientStub(), collection_name="property_v3")

    items = await repo.get_by_keyword("公七公園")

    assert [item.id for item in items] == ["place-1"]
    assert collection.find.call_args.args[0] == {
        "$and": [
            {"is_deleted": {"$ne": True}},
            {
                "$or": [
                    {"name": {"$regex": "公七公園", "$options": "i"}},
                    {"aliases": {"$regex": "公七公園", "$options": "i"}},
                    {"address": {"$regex": "公七公園", "$options": "i"}},
                ]
            },
        ]
    }


@pytest.mark.asyncio
async def test_get_in_bbox_applies_geo_keyword_and_category_filters():
    find_cursor = MagicMock()
    find_cursor.sort.return_value = find_cursor
    find_cursor.limit.return_value = find_cursor
    find_cursor.max_time_ms.return_value = find_cursor
    find_cursor.to_list = AsyncMock(return_value=[])
    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=2)
    collection.find.return_value = find_cursor

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = PropertyRepository(client=ClientStub(), collection_name="property_v3")

    items, total = await repo.get_in_bbox(
        min_lat=25.0,
        max_lat=25.1,
        min_lng=121.5,
        max_lng=121.6,
        types=["cafe", "bakery"],
        query="台北",
        limit=200,
    )

    assert items == []
    assert total == 2
    expected_filter = {
        "$and": [
            {"is_deleted": {"$ne": True}},
            {
                "location": {
                    "$geoWithin": {"$box": [[121.5, 25.0], [121.6, 25.1]]}
                },
                "primary_type": {"$in": ["cafe", "bakery"]},
                "$or": [
                    {"name": {"$regex": "[台臺]北", "$options": "i"}},
                    {"aliases": {"$regex": "[台臺]北", "$options": "i"}},
                    {"address": {"$regex": "[台臺]北", "$options": "i"}},
                ],
            },
        ]
    }
    assert collection.count_documents.await_args.args[0] == expected_filter
    assert collection.find.call_args.args[0] == expected_filter


@pytest.mark.asyncio
async def test_get_in_bbox_omits_optional_filters_when_not_provided():
    find_cursor = MagicMock()
    find_cursor.sort.return_value = find_cursor
    find_cursor.limit.return_value = find_cursor
    find_cursor.max_time_ms.return_value = find_cursor
    find_cursor.to_list = AsyncMock(return_value=[])
    collection = MagicMock()
    collection.count_documents = AsyncMock(return_value=0)
    collection.find.return_value = find_cursor

    class ClientStub:
        def get_collection(self, _collection_name: str):
            return collection

    repo = PropertyRepository(client=ClientStub(), collection_name="property_v3")

    await repo.get_in_bbox(
        min_lat=25.0,
        max_lat=25.1,
        min_lng=121.5,
        max_lng=121.6,
        types=[],
        query=None,
        limit=100,
    )

    assert collection.find.call_args.args[0] == {
        "$and": [
            {"is_deleted": {"$ne": True}},
            {
                "location": {
                    "$geoWithin": {"$box": [[121.5, 25.0], [121.6, 25.1]]}
                }
            },
        ]
    }
