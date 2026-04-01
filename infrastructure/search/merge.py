from typing import Any

from application.property_search_rules import FEATURE_FIELD_MAP, TRANSPORT_LABELS
from domain.entities.property import PropertyFilterCondition
from domain.entities.property_category import get_primary_types_by_category_key
from domain.entities.search import (
    CategoryIntent,
    DistanceIntent,
    LocationIntent,
    PetFeatureIntent,
    QualityIntent,
    SearchPlan,
)
from infrastructure.search.state import SearchGraphState


def build_semantic_summary(
    location_intent: LocationIntent,
    category_intent: CategoryIntent,
    feature_intent: PetFeatureIntent,
    quality_intent: QualityIntent,
    distance_intent: DistanceIntent,
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if location_intent.kind == "landmark" and location_intent.value:
        summary["landmark"] = location_intent.value
    elif location_intent.kind == "address" and location_intent.value:
        summary["address"] = location_intent.value

    if category_intent.primary_type:
        summary["category"] = category_intent.primary_type
    elif category_intent.category_key:
        summary["category"] = category_intent.category_key.value

    truthy_features = {
        feature_name: feature_value
        for feature_name, feature_value in feature_intent.features.items()
        if feature_value is True
    }
    if truthy_features:
        summary["preferences"] = truthy_features

    if quality_intent.min_rating is not None:
        summary["min_rating"] = quality_intent.min_rating

    if quality_intent.is_open is not None:
        summary["is_open"] = quality_intent.is_open

    if distance_intent.travel_time_limit_min is not None:
        summary["travel_time_limit_min"] = distance_intent.travel_time_limit_min

    if distance_intent.search_radius_meters is not None:
        summary["search_radius_meters"] = distance_intent.search_radius_meters

    if distance_intent.travel_time_limit_min is not None:
        summary["transport_mode"] = distance_intent.transport_mode

    return summary


def merge_plan_node(state: SearchGraphState) -> dict[str, Any]:
    location_intent = state.get("location_intent", LocationIntent())
    category_intent = state.get("category_intent", CategoryIntent())
    feature_intent = state.get("feature_intent", PetFeatureIntent())
    quality_intent = state.get("quality_intent", QualityIntent())
    distance_intent = state.get("distance_intent", DistanceIntent())

    mongo_query: dict[str, Any] = {}
    matched_fields: list[str] = []
    preferences: list[dict[str, str]] = []

    if location_intent.kind == "address" and location_intent.value:
        mongo_query["address"] = {"$regex": location_intent.value, "$options": "i"}
        matched_fields.append("address")
        preferences.append({"key": "address_preference", "label": location_intent.value})

    if category_intent.primary_type:
        mongo_query["primary_type"] = category_intent.primary_type
        matched_fields.append("primary_type")
        preferences.append(
            {
                "key": "primary_type_preference",
                "label": category_intent.primary_type,
            }
        )
    elif category_intent.category_key:
        primary_types = get_primary_types_by_category_key(category_intent.category_key)
        if primary_types:
            mongo_query["primary_type"] = {"$in": primary_types}
            matched_fields.append("primary_type")
            preferences.append(
                {
                    "key": "category_preference",
                    "label": category_intent.category_key.value,
                }
            )

    for feature_name, feature_value in feature_intent.features.items():
        if feature_value not in (True, False):
            continue
        field_path = FEATURE_FIELD_MAP.get(feature_name)
        if not field_path:
            continue
        mongo_query[field_path] = feature_value
        matched_fields.append(feature_name)
        preferences.append(
            {
                "key": f"{feature_name}_preference",
                "label": f"{feature_name}={feature_value}",
            }
        )

    if quality_intent.is_open is not None:
        mongo_query["is_open"] = quality_intent.is_open
        matched_fields.append("is_open")
        preferences.append({"key": "is_open_preference", "label": "營業中"})

    if distance_intent.travel_time_limit_min is not None:
        matched_fields.append("travel_time_limit_min")
        preferences.append(
            {
                "key": "travel_time_preference",
                "label": (
                    f"{distance_intent.travel_time_limit_min}分鐘"
                    f"{TRANSPORT_LABELS[distance_intent.transport_mode]}"
                ),
            }
        )

    landmark_context = (
        location_intent.value
        if location_intent.kind == "landmark" and location_intent.value
        else None
    )

    explanation_parts = [
        state["route_decision"].reason,
        location_intent.evidence,
        category_intent.evidence,
        feature_intent.evidence,
        quality_intent.evidence,
        distance_intent.evidence,
    ]
    explanation = " | ".join(part for part in explanation_parts if part)

    filter_condition = PropertyFilterCondition(
        mongo_query=mongo_query,
        matched_fields=matched_fields,
        preferences=preferences,
        min_rating=quality_intent.min_rating or 0.0,
        landmark_context=landmark_context,
        travel_time_limit_min=distance_intent.travel_time_limit_min,
        search_radius_meters=(
            distance_intent.search_radius_meters
            if distance_intent.search_radius_meters is not None
            else 100000
        ),
        explanation=explanation,
    )

    plan = SearchPlan(
        route="semantic",
        route_reason=state["route_decision"].reason,
        route_confidence=state["route_decision"].confidence,
        filter_condition=filter_condition,
        semantic_extraction=build_semantic_summary(
            location_intent=location_intent,
            category_intent=category_intent,
            feature_intent=feature_intent,
            quality_intent=quality_intent,
            distance_intent=distance_intent,
        ),
    )
    return {"plan": plan}


def confidence_gate_node(state: SearchGraphState) -> dict[str, Any]:
    plan = state["plan"]
    location_intent = state.get("location_intent", LocationIntent())
    category_intent = state.get("category_intent", CategoryIntent())
    feature_intent = state.get("feature_intent", PetFeatureIntent())
    quality_intent = state.get("quality_intent", QualityIntent())
    distance_intent = state.get("distance_intent", DistanceIntent())

    fallback_reason = None
    warnings = list(plan.warnings)
    recognized_any = bool(
        plan.semantic_extraction
        or plan.filter_condition.mongo_query
        or plan.filter_condition.landmark_context
        or plan.filter_condition.travel_time_limit_min is not None
    )

    if not recognized_any:
        fallback_reason = "semantic_parse_empty"
    elif (
        not category_intent.primary_type
        and not category_intent.category_key
        and location_intent.kind != "address"
        and not plan.filter_condition.landmark_context
        and not feature_intent.features
        and quality_intent.is_open is None
        and quality_intent.min_rating is None
        and distance_intent.travel_time_limit_min is None
    ):
        fallback_reason = "semantic_parse_missing_core_constraints"

    if (
        not fallback_reason
        and location_intent.kind != "none"
        and location_intent.value
        and location_intent.confidence < 0.7
    ):
        warnings.append("low_confidence_location")
        if location_intent.kind == "address":
            plan.filter_condition.mongo_query.pop("address", None)
            plan.filter_condition.matched_fields = [
                field
                for field in plan.filter_condition.matched_fields
                if field != "address"
            ]
            plan.filter_condition.preferences = [
                preference
                for preference in plan.filter_condition.preferences
                if preference.get("key") != "address_preference"
            ]
            plan.semantic_extraction.pop("address", None)
        elif location_intent.kind == "landmark":
            plan.filter_condition.landmark_context = None
            plan.semantic_extraction.pop("landmark", None)

    if (
        category_intent.primary_type or category_intent.category_key
    ) and category_intent.confidence < 0.7:
        warnings.append("low_confidence_primary_type")

    if feature_intent.features and feature_intent.confidence < 0.7:
        warnings.append("low_confidence_pet_features")

    if quality_intent.min_rating is not None and quality_intent.confidence < 0.65:
        warnings.append("low_confidence_quality")

    if (
        distance_intent.travel_time_limit_min is not None
        and distance_intent.confidence < 0.7
    ):
        warnings.append("low_confidence_distance")

    plan.warnings = warnings
    if fallback_reason:
        plan.used_fallback = True
        plan.fallback_reason = fallback_reason

    return {"plan": plan}


def keyword_plan_node(state: SearchGraphState) -> dict[str, Any]:
    decision = state["route_decision"]
    plan = SearchPlan(
        route="keyword",
        route_reason=decision.reason,
        route_confidence=decision.confidence,
        filter_condition=PropertyFilterCondition(explanation=decision.reason),
    )
    return {"plan": plan}
