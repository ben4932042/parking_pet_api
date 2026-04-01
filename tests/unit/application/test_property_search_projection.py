from domain.entities.enrichment import (
    AIAnalysis,
    PetEnvironment,
    PetFeatures,
    PetRules,
    PetService,
)
from domain.entities.property import PropertyEntity
from application.property_search.projection import build_property_alias_fields


def build_property(*, name: str, primary_type: str, venue_type: str) -> PropertyEntity:
    return PropertyEntity(
        _id="place-1",
        name=name,
        place_id="place-1",
        latitude=25.03,
        longitude=121.56,
        regular_opening_hours=[],
        address="台灣",
        primary_type=primary_type,
        ai_analysis=AIAnalysis(
            venue_type=venue_type,
            ai_summary="summary",
            pet_features=PetFeatures(
                rules=PetRules(),
                environment=PetEnvironment(),
                services=PetService(),
            ),
            highlights=[],
            warnings=[],
            rating=4.0,
        ),
    )


def test_build_property_alias_fields_strips_branch_suffix_after_at():
    property_entity = build_property(
        name="Frankie Feels Good @______ corner",
        primary_type="food_store",
        venue_type="複合式餐飲空間",
    )

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["Frankie Feels Good"]


def test_build_property_alias_fields_extracts_park_alias_and_category():
    property_entity = build_property(
        name="青埔公七公園",
        primary_type="park",
        venue_type="寵物友善公園",
    )

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["公七公園"]


def test_build_property_alias_fields_merges_manual_aliases_without_duplicates():
    property_entity = build_property(
        name="青埔公七公園",
        primary_type="park",
        venue_type="寵物友善公園",
    ).model_copy(update={"manual_aliases": ["  公七公園  ", "青埔七號公園"]})

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["公七公園", "青埔七號公園"]


def test_build_property_alias_fields_strips_chinese_branch_suffix():
    property_entity = build_property(
        name="肉球森林 台北101店",
        primary_type="cafe",
        venue_type="寵物友善餐飲",
    )

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["肉球森林"]


def test_build_property_alias_fields_strips_separator_suffix_note():
    property_entity = build_property(
        name="某某咖啡 - 審計新村店",
        primary_type="cafe",
        venue_type="寵物友善餐飲",
    )

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["某某咖啡"]


def test_build_property_alias_fields_strips_english_location_suffix():
    property_entity = build_property(
        name="Brand X Taichung",
        primary_type="pet_store",
        venue_type="寵物用品空間",
    )

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["Brand X"]


def test_build_property_alias_fields_strips_trailhead_suffix():
    property_entity = build_property(
        name="橫嶺山步道入口",
        primary_type="hiking_area",
        venue_type="戶外步道",
    )

    payload = build_property_alias_fields(property_entity)

    assert payload["aliases"] == ["橫嶺山步道"]
