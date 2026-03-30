from domain.entities.enrichment import (
    AIAnalysis,
    PetEnvironment,
    PetFeatures,
    PetRules,
    PetService,
)
from domain.entities.property import OpeningPeriod, PropertyEntity, TimePoint
from domain.entities.property_category import (
    PROPERTY_CATEGORIES,
    PropertyCategoryKey,
    get_categories_by_primary_type,
    get_primary_category_key,
    get_primary_types_by_category_key,
)


def test_list_property_categories_contains_expected_keys():
    keys = {category.key for category in PROPERTY_CATEGORIES}

    assert keys == {
        PropertyCategoryKey.RESTAURANT,
        PropertyCategoryKey.CAFE,
        PropertyCategoryKey.OUTDOOR,
        PropertyCategoryKey.PET_HOSPITAL,
        PropertyCategoryKey.PET_SUPPLIES,
        PropertyCategoryKey.PET_GROOMING,
        PropertyCategoryKey.LODGING,
    }


def test_dessert_shop_maps_to_cafe():
    match = get_categories_by_primary_type("dessert_shop")

    assert [category.key for category in match] == [PropertyCategoryKey.CAFE]


def test_pet_care_maps_to_pet_grooming():
    match = get_categories_by_primary_type("pet_care")

    assert [category.key for category in match] == [PropertyCategoryKey.PET_GROOMING]


def test_restaurant_category_contains_brunch_and_bar():
    restaurant_category = next(
        category
        for category in PROPERTY_CATEGORIES
        if category.key == PropertyCategoryKey.RESTAURANT
    )

    assert "brunch_restaurant" in restaurant_category.primary_types
    assert "bar" in restaurant_category.primary_types


def test_unknown_primary_type_returns_empty_mapping():
    assert get_categories_by_primary_type("not_a_real_type") == []


def test_property_entity_generates_overview_category_from_primary_type():
    entity = PropertyEntity(
        _id="p1",
        name="Dessert Cafe",
        place_id="p1",
        latitude=25.03,
        longitude=121.56,
        regular_opening_hours=[
            OpeningPeriod(
                open=TimePoint(day=0, hour=0, minute=0),
                close=TimePoint(day=6, hour=23, minute=59),
            )
        ],
        address="test",
        primary_type="dessert_shop",
        ai_analysis=AIAnalysis(
            venue_type="dessert cafe",
            ai_summary="summary",
            pet_features=PetFeatures(
                rules=PetRules(
                    leash_required=False, stroller_required=False, allow_on_floor=False
                ),
                environment=PetEnvironment(
                    stairs=False,
                    outdoor_seating=False,
                    spacious=False,
                    indoor_ac=True,
                    off_leash_possible=False,
                    pet_friendly_floor=True,
                    has_shop_pet=False,
                ),
                services=PetService(
                    pet_menu=False,
                    free_water=False,
                    free_treats=False,
                    pet_seating=False,
                ),
            ),
            highlights=[],
            warnings=[],
            rating=4.0,
        ),
    )

    assert entity.category == "cafe"


def test_primary_category_key_returns_english_key():
    assert get_primary_category_key("dessert_shop") == "cafe"
    assert get_primary_category_key("pet_care") == "pet_grooming"


def test_category_key_returns_primary_types_for_nearby_filter():
    primary_types = get_primary_types_by_category_key(PropertyCategoryKey.RESTAURANT)

    assert "restaurant" in primary_types
    assert "brunch_restaurant" in primary_types
    assert "bar" in primary_types
