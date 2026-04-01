from typing import TypedDict

from domain.entities.search import (
    CategoryIntent,
    DistanceIntent,
    LocationIntent,
    PetFeatureIntent,
    QualityIntent,
    SearchPlan,
    SearchRouteDecision,
    TimeIntent,
    TypoCorrectionIntent,
)


class SearchGraphState(TypedDict, total=False):
    raw_query: str
    query_text: str
    typo_intent: TypoCorrectionIntent
    route_decision: SearchRouteDecision
    location_intent: LocationIntent
    category_intent: CategoryIntent
    feature_intent: PetFeatureIntent
    quality_intent: QualityIntent
    time_intent: TimeIntent
    distance_intent: DistanceIntent
    plan: SearchPlan
