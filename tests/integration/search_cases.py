from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryChecks:
    primary_type_includes: str | None = None
    max_distance: int | None = None
    address_regex: str | None = None
    is_open: bool | None = None
    feature_equals: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchConditionCase:
    query: str
    params: dict[str, float]
    response_type: str
    preferences: tuple[str, ...]
    landmark_context: str | None
    travel_time_limit_min: int | None
    search_radius_meters: int
    transport_mode: str | None
    query_checks: QueryChecks


SEARCH_CONDITION_CASES = [
    SearchConditionCase(
        query="想吃點心",
        params={},
        response_type="semantic_search",
        preferences=("category_preference",),
        landmark_context=None,
        travel_time_limit_min=None,
        search_radius_meters=100000,
        transport_mode=None,
        query_checks=QueryChecks(primary_type_includes="cafe"),
    ),
    SearchConditionCase(
        query="距離30分鐘車程的咖啡廳",
        params={"user_lat": 25.0339, "user_lng": 121.5645},
        response_type="semantic_search",
        preferences=("category_preference", "travel_time_preference"),
        landmark_context="CURRENT_LOCATION",
        travel_time_limit_min=30,
        search_radius_meters=22500,
        transport_mode="driving",
        query_checks=QueryChecks(primary_type_includes="cafe", max_distance=22500),
    ),
    SearchConditionCase(
        query="步行15分鐘的公園",
        params={"user_lat": 25.0339, "user_lng": 121.5645},
        response_type="semantic_search",
        preferences=("primary_type_preference", "travel_time_preference"),
        landmark_context="CURRENT_LOCATION",
        travel_time_limit_min=15,
        search_radius_meters=1125,
        transport_mode="walking",
        query_checks=QueryChecks(primary_type_includes="park", max_distance=1125),
    ),
    SearchConditionCase(
        query="開車十分鐘的公園",
        params={"user_lat": 25.0339, "user_lng": 121.5645},
        response_type="semantic_search",
        preferences=("primary_type_preference", "travel_time_preference"),
        landmark_context="CURRENT_LOCATION",
        travel_time_limit_min=10,
        search_radius_meters=7500,
        transport_mode="driving",
        query_checks=QueryChecks(primary_type_includes="park", max_distance=7500),
    ),
    SearchConditionCase(
        query="走路五分鐘的咖啡廳",
        params={"user_lat": 25.0339, "user_lng": 121.5645},
        response_type="semantic_search",
        preferences=("category_preference", "travel_time_preference"),
        landmark_context="CURRENT_LOCATION",
        travel_time_limit_min=5,
        search_radius_meters=375,
        transport_mode="walking",
        query_checks=QueryChecks(primary_type_includes="cafe", max_distance=375),
    ),
    SearchConditionCase(
        query="青埔哪裡可以跑跑",
        params={},
        response_type="semantic_search",
        preferences=(),
        landmark_context="青埔",
        travel_time_limit_min=None,
        search_radius_meters=100000,
        transport_mode=None,
        query_checks=QueryChecks(max_distance=100000),
    ),
    SearchConditionCase(
        query="台北101附近咖啡廳",
        params={},
        response_type="semantic_search",
        preferences=("category_preference",),
        landmark_context="台北101",
        travel_time_limit_min=None,
        search_radius_meters=100000,
        transport_mode=None,
        query_checks=QueryChecks(primary_type_includes="cafe", max_distance=100000),
    ),
    SearchConditionCase(
        query="現在有開的台北咖啡廳",
        params={},
        response_type="semantic_search",
        preferences=(
            "address_preference",
            "category_preference",
            "is_open_preference",
        ),
        landmark_context=None,
        travel_time_limit_min=None,
        search_radius_meters=100000,
        transport_mode=None,
        query_checks=QueryChecks(address_regex="台北", is_open=True),
    ),
    SearchConditionCase(
        query="沒有店狗 寵物可落地的咖啡廳",
        params={},
        response_type="semantic_search",
        preferences=(
            "category_preference",
            "has_shop_pet_preference",
            "allow_on_floor_preference",
        ),
        landmark_context=None,
        travel_time_limit_min=None,
        search_radius_meters=100000,
        transport_mode=None,
        query_checks=QueryChecks(
            primary_type_includes="cafe",
            feature_equals={
                "effective_pet_features.environment.has_shop_pet": False,
                "effective_pet_features.rules.allow_on_floor": True,
            },
        ),
    ),
]
