from infrastructure.mongo.property import PropertyRepository
from unittest.mock import AsyncMock

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
