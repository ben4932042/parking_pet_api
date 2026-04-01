import math
from typing import Any, List, Optional

from domain.entities.property import PropertyEntity


def rank_search_results(items: List[PropertyEntity], query: dict) -> List[PropertyEntity]:
    type_filter = query.get("primary_type")
    is_open_required = query.get("is_open") is True
    requested_feature_paths = _requested_feature_paths(query)
    geo_context = _extract_geo_context(query)

    return sorted(
        items,
        key=lambda item: score_search_result(
            item=item,
            type_filter=type_filter,
            is_open_required=is_open_required,
            requested_feature_paths=requested_feature_paths,
            geo_context=geo_context,
        ),
        reverse=True,
    )


def score_search_result(
    item: PropertyEntity,
    type_filter: Any,
    is_open_required: bool,
    requested_feature_paths: List[str],
    geo_context: Optional[dict[str, Any]],
) -> float:
    rating_score = max(0.0, min((item.ai_analysis.ai_rating or 0.0) / 5.0, 1.0))
    pet_feature_score = _pet_feature_score(item)
    requested_feature_score = _requested_feature_score(item, requested_feature_paths)
    distance_score = _distance_score(item, geo_context)
    type_score = _type_score(item, type_filter)
    open_score = 0.05 if is_open_required and item.is_open else 0.0

    return (
        (rating_score * 0.45)
        + (pet_feature_score * 0.20)
        + (requested_feature_score * 0.15)
        + (distance_score * 0.15)
        + type_score
        + open_score
    )


def _type_score(item: PropertyEntity, type_filter: Any) -> float:
    if not type_filter:
        return 0.0

    if isinstance(type_filter, dict) and "$in" in type_filter:
        return 0.05 if item.primary_type in type_filter["$in"] else 0.0

    return 0.05 if item.primary_type == type_filter else 0.0


def _pet_feature_score(item: PropertyEntity) -> float:
    pet_features = (item.effective_pet_features or item.ai_analysis.pet_features).model_dump()
    bool_values: List[bool] = []

    def _collect(values: Any) -> None:
        if isinstance(values, dict):
            for nested in values.values():
                _collect(nested)
        elif isinstance(values, bool):
            bool_values.append(values)

    _collect(pet_features)
    if not bool_values:
        return 0.0

    return sum(1 for value in bool_values if value) / len(bool_values)


def _requested_feature_paths(query: dict) -> List[str]:
    return [
        key
        for key, value in query.items()
        if key.startswith("effective_pet_features.") and isinstance(value, bool)
    ]


def _requested_feature_score(item: PropertyEntity, requested_feature_paths: List[str]) -> float:
    if not requested_feature_paths:
        return 0.0

    matched = sum(
        1 for path in requested_feature_paths if _get_nested_value(item.model_dump(), path) is True
    )
    return matched / len(requested_feature_paths)


def _extract_geo_context(query: dict) -> Optional[dict[str, Any]]:
    location_query = query.get("location", {})
    near_query = location_query.get("$nearSphere")
    if not near_query:
        return None

    geometry = near_query.get("$geometry", {})
    coordinates = geometry.get("coordinates")
    max_distance = near_query.get("$maxDistance")
    if (
        not isinstance(coordinates, list)
        or len(coordinates) != 2
        or coordinates[0] is None
        or coordinates[1] is None
        or not max_distance
    ):
        return None

    return {"coordinates": (coordinates[0], coordinates[1]), "max_distance": max_distance}


def _distance_score(item: PropertyEntity, geo_context: Optional[dict[str, Any]]) -> float:
    if not geo_context:
        return 0.0

    anchor_lng, anchor_lat = geo_context["coordinates"]
    distance_meters = _haversine_meters(
        lat1=anchor_lat,
        lng1=anchor_lng,
        lat2=item.latitude,
        lng2=item.longitude,
    )
    max_distance = geo_context["max_distance"]
    if max_distance <= 0:
        return 0.0

    return max(0.0, 1.0 - (distance_meters / max_distance))


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def _get_nested_value(payload: dict, path: str) -> Any:
    current: Any = payload
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current
