from enum import StrEnum

from pydantic import BaseModel, Field


class PropertyCategoryKey(StrEnum):
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    OUTDOOR = "outdoor"
    PET_HOSPITAL = "pet_hospital"
    PET_SUPPLIES = "pet_supplies"
    PET_GROOMING = "pet_grooming"
    LODGING = "lodging"


class PropertyCategoryEntity(BaseModel):
    key: PropertyCategoryKey
    label: str
    primary_types: list[str] = Field(default_factory=list)


class PropertyCategoryMatchEntity(BaseModel):
    primary_type: str
    categories: list[PropertyCategoryEntity] = Field(default_factory=list)


PROPERTY_CATEGORIES: list[PropertyCategoryEntity] = [
    PropertyCategoryEntity(
        key=PropertyCategoryKey.RESTAURANT,
        label="餐廳",
        primary_types=[
            "restaurant",
            "afghani_restaurant",
            "african_restaurant",
            "american_restaurant",
            "asian_fusion_restaurant",
            "asian_restaurant",
            "australian_restaurant",
            "austrian_restaurant",
            "bangladeshi_restaurant",
            "bar",
            "bar_and_grill",
            "barbecue_restaurant",
            "basque_restaurant",
            "bistro",
            "breakfast_restaurant",
            "brunch_restaurant",
            "buffet_restaurant",
            "chinese_restaurant",
            "diner",
            "fast_food_restaurant",
            "fine_dining_restaurant",
            "french_restaurant",
            "greek_restaurant",
            "hamburger_restaurant",
            "hot_dog_restaurant",
            "hot_pot_restaurant",
            "indian_restaurant",
            "indonesian_restaurant",
            "italian_restaurant",
            "japanese_restaurant",
            "korean_restaurant",
            "lebanese_restaurant",
            "mediterranean_restaurant",
            "mexican_restaurant",
            "middle_eastern_restaurant",
            "pizza_restaurant",
            "ramen_restaurant",
            "seafood_restaurant",
            "spanish_restaurant",
            "steak_house",
            "sushi_restaurant",
            "thai_restaurant",
            "turkish_restaurant",
            "vegan_restaurant",
            "vegetarian_restaurant",
            "vietnamese_restaurant",
            "noodle_shop",
        ],
    ),
    PropertyCategoryEntity(
        key=PropertyCategoryKey.CAFE,
        label="咖啡廳",
        primary_types=[
            "cafe",
            "coffee_shop",
            "dessert_shop",
            "bakery",
            "bagel_shop",
            "acai_shop",
            "tea_house",
            "food_store",
            "coffee_roastery",
            "food_store",
            "dog_cafe",
        ],
    ),
    PropertyCategoryEntity(
        key=PropertyCategoryKey.OUTDOOR,
        label="戶外活動",
        primary_types=[
            "park",
            "dog_park",
            "hiking_area",
            "garden",
            "national_park",
            "state_park",
            "city_park",
            "school",
            "secondary_school",
            "university",
            "library",
            "preschool",
            "primary_school",
            "athletic_field",
        ],
    ),
    PropertyCategoryEntity(
        key=PropertyCategoryKey.PET_HOSPITAL,
        label="寵物醫院",
        primary_types=[
            "veterinary_care",
        ],
    ),
    PropertyCategoryEntity(
        key=PropertyCategoryKey.PET_SUPPLIES,
        label="寵物用品店",
        primary_types=[
            "pet_store",
            "store",
        ],
    ),
    PropertyCategoryEntity(
        key=PropertyCategoryKey.PET_GROOMING,
        label="寵物美容",
        primary_types=[
            "pet_care",
        ],
    ),
    PropertyCategoryEntity(
        key=PropertyCategoryKey.LODGING,
        label="住宿",
        primary_types=[
            "pet_boarding_service",
            "bed_and_breakfast",
            "budget_japanese_inn",
            "campground",
            "camping_cabin",
            "cottage",
            "extended_stay_hotel",
            "farmstay",
            "guest_house",
            "hostel",
            "hotel",
            "inn",
            "japanese_inn",
            "lodging",
            "mobile_home_park",
            "motel",
            "private_guest_room",
            "resort_hotel",
            "rv_park",
        ],
    ),
]


def get_categories_by_primary_type(primary_type: str) -> list[PropertyCategoryEntity]:
    return [
        category
        for category in PROPERTY_CATEGORIES
        if primary_type in category.primary_types
    ]


def get_primary_category_label(primary_type: str) -> str | None:
    matched = get_categories_by_primary_type(primary_type)
    if not matched:
        return None
    return matched[0].label


def get_primary_category_key(primary_type: str) -> str | None:
    matched = get_categories_by_primary_type(primary_type)
    if not matched:
        return None
    return matched[0].key.value


def get_primary_types_by_category_key(
    category_key: PropertyCategoryKey | None,
) -> list[str]:
    if category_key is None:
        return []

    for category in PROPERTY_CATEGORIES:
        if category.key == category_key:
            return category.primary_types
    return []
