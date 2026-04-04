from application.property_search.planning import (
    apply_confidence_gate,
    build_keyword_plan,
    build_search_plan,
)
from domain.entities.search import (
    CategoryIntent,
    DistanceIntent,
    LocationIntent,
    PetFeatureIntent,
    QualityIntent,
    TimeIntent,
)
from infrastructure.search.state import SearchGraphState


def merge_plan_node(state: SearchGraphState) -> dict:
    plan = build_search_plan(
        execution_modes=state["route_decision"].execution_modes,
        route_reason=state["route_decision"].reason,
        route_confidence=state["route_decision"].confidence,
        location_intent=state.get("location_intent", LocationIntent()),
        category_intent=state.get("category_intent", CategoryIntent()),
        feature_intent=state.get("feature_intent", PetFeatureIntent()),
        quality_intent=state.get("quality_intent", QualityIntent()),
        time_intent=state.get("time_intent", TimeIntent()),
        distance_intent=state.get("distance_intent", DistanceIntent()),
    )
    return {"plan": plan}


def confidence_gate_node(state: SearchGraphState) -> dict:
    plan = apply_confidence_gate(
        plan=state["plan"],
        location_intent=state.get("location_intent", LocationIntent()),
        category_intent=state.get("category_intent", CategoryIntent()),
        feature_intent=state.get("feature_intent", PetFeatureIntent()),
        quality_intent=state.get("quality_intent", QualityIntent()),
        time_intent=state.get("time_intent", TimeIntent()),
        distance_intent=state.get("distance_intent", DistanceIntent()),
    )
    return {"plan": plan}


def keyword_plan_node(state: SearchGraphState) -> dict:
    decision = state["route_decision"]
    return {
        "plan": build_keyword_plan(
            route_reason=decision.reason,
            route_confidence=decision.confidence,
        )
    }
