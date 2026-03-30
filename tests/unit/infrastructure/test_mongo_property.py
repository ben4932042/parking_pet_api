from infrastructure.mongo.property import PropertyRepository


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
