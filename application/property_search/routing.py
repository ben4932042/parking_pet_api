from domain.entities.search import LocationIntent, SearchRouteDecision

from application.property_search.rules import (
    extract_address_by_rule,
    extract_category_by_rule,
    extract_distance_by_rule,
    extract_feature_by_rule,
    extract_landmark_by_rule,
    extract_quality_by_rule,
    extract_time_by_rule,
    is_basic_prompt_injection,
    is_obviously_non_search_query,
    normalize_llm_execution_modes,
    normalize_text_for_match,
    should_run_keyword_with_semantic,
    should_use_current_location_context,
)


def route_decision_by_rule(
    query: str,
) -> tuple[SearchRouteDecision, LocationIntent | None] | None:
    if is_basic_prompt_injection(query):
        return (
            SearchRouteDecision(
                execution_modes=["keyword"],
                confidence=0.99,
                reason="查詢包含 prompt injection 訊號，改用關鍵字搜尋",
            ),
            None,
        )

    if is_obviously_non_search_query(query):
        return (
            SearchRouteDecision(
                execution_modes=["keyword"],
                confidence=0.98,
                reason="查詢內容不像搜尋條件，直接回傳空結果",
            ),
            None,
        )

    rule_based_address = extract_address_by_rule(query)
    rule_based_category = extract_category_by_rule(query)
    rule_based_feature = extract_feature_by_rule(query)
    rule_based_quality = extract_quality_by_rule(query)
    rule_based_time = extract_time_by_rule(query)
    rule_based_distance = extract_distance_by_rule(query)
    normalized_query = normalize_text_for_match(query)

    if rule_based_address and normalized_query == rule_based_address:
        return (
            SearchRouteDecision(
                execution_modes=["semantic"],
                confidence=0.98,
                reason="查詢本身就是行政區或地址條件",
            ),
            None,
        )

    if rule_based_address and rule_based_category:
        return (
            SearchRouteDecision(
                execution_modes=["semantic"],
                confidence=0.98,
                reason="包含地點和分類條件",
            ),
            None,
        )

    rule_based_landmark = extract_landmark_by_rule(query)
    if rule_based_landmark:
        return (
            SearchRouteDecision(
                execution_modes=["semantic"],
                confidence=0.98,
                reason="查詢本身就是地標條件",
            ),
            LocationIntent(
                kind="landmark",
                value=rule_based_landmark,
                confidence=0.98,
                evidence="matched landmark keyword or suffix by rule",
            ),
        )

    if (
        rule_based_category
        or rule_based_feature
        or rule_based_quality
        or rule_based_time
        or rule_based_distance
        or should_use_current_location_context(query)
    ):
        execution_modes = ["semantic"]
        if should_run_keyword_with_semantic(query):
            execution_modes.append("keyword")
        return (
            SearchRouteDecision(
                execution_modes=execution_modes,
                confidence=0.95,
                reason="查詢包含分類或偏好條件",
            ),
            None,
        )

    return None


def should_use_llm_location_as_route(
    query: str,
    location_intent: LocationIntent,
) -> bool:
    normalized_query = normalize_text_for_match(query)
    normalized_landmark = normalize_text_for_match(location_intent.value or "")
    return bool(
        location_intent.kind == "landmark"
        and location_intent.value
        and (
            normalized_query in normalized_landmark
            or normalized_landmark in normalized_query
        )
        and location_intent.confidence >= 0.7
    )


def normalize_router_decision(
    query: str,
    decision: SearchRouteDecision,
) -> SearchRouteDecision:
    decision.execution_modes = normalize_llm_execution_modes(
        query,
        decision.execution_modes,
    )
    return decision
