import json
from typing import Any

from application.property_search.planning import (
    apply_confidence_gate,
    build_keyword_plan,
    build_search_plan,
)
from application.property_search.routing import (
    normalize_router_decision,
    route_decision_by_rule,
    should_use_llm_location_as_route,
)
from application.property_search.rules import (
    extract_address_by_rule,
    extract_category_by_rule,
    extract_distance_by_rule,
    extract_feature_by_rule,
    extract_landmark_by_rule,
    extract_quality_by_rule,
    extract_time_by_rule,
    has_feature_hints,
    has_quality_hints,
    has_time_hints,
    normalize_category_intent,
    should_run_typo_normalizer,
    should_use_current_location_context,
)
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

from domain.entities.property import PropertyEntity
from domain.entities.property_category import PROPERTY_CATEGORIES
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
from infrastructure.search.prompts import (
    CATEGORY_PARSER_PROMPT,
    FEATURE_PARSER_PROMPT,
    LOCATION_PARSER_PROMPT,
    QUALITY_PARSER_PROMPT,
    ROUTER_PROMPT,
    TYPO_NORMALIZER_PROMPT,
)
from infrastructure.search.state import SearchGraphState


def invoke_structured(
    llm,
    system_prompt: str,
    user_input: str,
    schema,
    extra_variables: dict[str, Any] | None = None,
):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{user_input}"),
        ]
    )
    chain = prompt | llm.with_structured_output(schema)
    payload = {"user_input": user_input}
    if extra_variables:
        payload.update(extra_variables)
    return chain.invoke(payload)


def current_query(state: SearchGraphState) -> str:
    return state.get("query_text") or state["raw_query"]


def semantic_fanout_node(state: SearchGraphState) -> SearchGraphState:
    return state


def typo_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    if not should_run_typo_normalizer(query):
        return {
            "query_text": query,
            "typo_intent": TypoCorrectionIntent(
                corrected_query=query,
                changed=False,
                confidence=1.0,
                evidence="skip typo normalization by heuristic",
            ),
        }

    intent = invoke_structured(
        llm=llm,
        system_prompt=TYPO_NORMALIZER_PROMPT,
        user_input=query,
        schema=TypoCorrectionIntent,
    )
    corrected_query = (intent.corrected_query or query).strip() or query

    if not intent.changed or intent.confidence < 0.75:
        corrected_query = query
        intent = TypoCorrectionIntent(
            corrected_query=query,
            changed=False,
            confidence=intent.confidence,
            evidence=intent.evidence or "typo normalizer kept original query",
        )

    return {"query_text": corrected_query, "typo_intent": intent}


def route_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    rule_based = route_decision_by_rule(query)
    if rule_based is not None:
        decision, location_intent = rule_based
        result: dict[str, Any] = {"route_decision": decision}
        if location_intent is not None:
            result["location_intent"] = location_intent
        return result

    entity_schema = PropertyEntity.model_json_schema()
    location_intent = invoke_structured(
        llm=llm,
        system_prompt=LOCATION_PARSER_PROMPT,
        user_input=query,
        schema=LocationIntent,
        extra_variables={"entity_schema": str(entity_schema)},
    )
    if should_use_llm_location_as_route(query, location_intent):
        return {
            "route_decision": SearchRouteDecision(
                execution_modes=["semantic"],
                confidence=location_intent.confidence,
                reason="查詢本身就是地標條件",
            ),
            "location_intent": location_intent,
        }

    decision = invoke_structured(
        llm=llm,
        system_prompt=ROUTER_PROMPT,
        user_input=query,
        schema=SearchRouteDecision,
    )
    decision = normalize_router_decision(query, decision)
    return {"route_decision": decision}


def location_node(llm, state: SearchGraphState) -> dict[str, Any]:
    existing_intent = state.get("location_intent")
    if existing_intent and existing_intent.kind != "none" and existing_intent.value:
        return {"location_intent": existing_intent}

    query = current_query(state)
    rule_based_address = extract_address_by_rule(query)
    if rule_based_address:
        return {
            "location_intent": LocationIntent(
                kind="address",
                value=rule_based_address,
                confidence=0.95,
                evidence="matched Taiwan administrative area or address suffix by rule",
            )
        }

    rule_based_landmark = extract_landmark_by_rule(query)
    if rule_based_landmark:
        return {
            "location_intent": LocationIntent(
                kind="landmark",
                value=rule_based_landmark,
                confidence=0.98,
                evidence="matched landmark keyword or suffix by rule",
            )
        }

    if should_use_current_location_context(query):
        return {
            "location_intent": LocationIntent(
                kind="landmark",
                value="CURRENT_LOCATION",
                confidence=0.95,
                evidence="travel-time query without explicit geo anchor defaults to CURRENT_LOCATION",
            )
        }

    if (
        extract_category_by_rule(query)
        or extract_feature_by_rule(query)
        or extract_quality_by_rule(query)
        or extract_time_by_rule(query)
        or extract_distance_by_rule(query)
    ):
        return {"location_intent": LocationIntent()}

    entity_schema = PropertyEntity.model_json_schema()
    intent = invoke_structured(
        llm=llm,
        system_prompt=LOCATION_PARSER_PROMPT,
        user_input=query,
        schema=LocationIntent,
        extra_variables={"entity_schema": str(entity_schema)},
    )
    return {"location_intent": intent}


def category_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    rule_based_landmark = extract_landmark_by_rule(query)
    rule_based_intent = extract_category_by_rule(query)
    if rule_based_landmark and not rule_based_intent:
        return {
            "category_intent": CategoryIntent(
                confidence=0.98,
                evidence="landmark-only query does not imply a place category",
            )
        }

    if rule_based_intent:
        return {"category_intent": rule_based_intent}

    property_categories = json.dumps(
        [category.model_dump(mode="json") for category in PROPERTY_CATEGORIES],
        ensure_ascii=False,
    )
    intent = invoke_structured(
        llm=llm,
        system_prompt=CATEGORY_PARSER_PROMPT,
        user_input=query,
        schema=CategoryIntent,
        extra_variables={"property_categories": property_categories},
    )
    return {"category_intent": normalize_category_intent(query, intent)}


def feature_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    rule_based_intent = extract_feature_by_rule(query)
    if rule_based_intent:
        return {"feature_intent": rule_based_intent}

    if not has_feature_hints(query):
        return {"feature_intent": PetFeatureIntent()}

    intent = invoke_structured(
        llm=llm,
        system_prompt=FEATURE_PARSER_PROMPT,
        user_input=query,
        schema=PetFeatureIntent,
    )
    return {"feature_intent": intent}


def quality_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    rule_based_intent = extract_quality_by_rule(query)
    if rule_based_intent:
        return {"quality_intent": rule_based_intent}

    if has_time_hints(query):
        return {"quality_intent": QualityIntent()}

    if not has_quality_hints(query):
        return {"quality_intent": QualityIntent()}

    intent = invoke_structured(
        llm=llm,
        system_prompt=QUALITY_PARSER_PROMPT,
        user_input=query,
        schema=QualityIntent,
    )
    return {"quality_intent": intent}


def time_node(state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    rule_based_intent = extract_time_by_rule(query)
    if rule_based_intent:
        return {"time_intent": rule_based_intent}

    if not has_time_hints(query):
        return {"time_intent": TimeIntent()}

    return {"time_intent": TimeIntent()}


def distance_node(state: SearchGraphState) -> dict[str, Any]:
    query = current_query(state)
    rule_based_intent = extract_distance_by_rule(query)
    if rule_based_intent:
        return {"distance_intent": rule_based_intent}

    return {"distance_intent": DistanceIntent()}


def next_after_router(state: SearchGraphState) -> str:
    return (
        "semantic"
        if "semantic" in state["route_decision"].execution_modes
        else "keyword"
    )


def next_after_gate(state: SearchGraphState) -> str:
    return "fallback" if state["plan"].used_fallback else "semantic"


def extract_search_plan(llm, user_input: str) -> SearchPlan:
    graph = StateGraph(SearchGraphState)
    graph.add_node("typo_normalizer", lambda state: typo_node(llm, state))
    graph.add_node("router", lambda state: route_node(llm, state))
    graph.add_node(
        "keyword_plan",
        lambda state: {
            "plan": build_keyword_plan(
                route_reason=state["route_decision"].reason,
                route_confidence=state["route_decision"].confidence,
            )
        },
    )
    graph.add_node("semantic_fanout", semantic_fanout_node)
    graph.add_node("location_parser", lambda state: location_node(llm, state))
    graph.add_node("category_parser", lambda state: category_node(llm, state))
    graph.add_node("feature_parser", lambda state: feature_node(llm, state))
    graph.add_node("quality_parser", lambda state: quality_node(llm, state))
    graph.add_node("time_parser", time_node)
    graph.add_node("distance_parser", distance_node)
    graph.add_node(
        "merge_plan",
        lambda state: {
            "plan": build_search_plan(
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
        },
    )
    graph.add_node(
        "confidence_gate",
        lambda state: {
            "plan": apply_confidence_gate(
                plan=state["plan"],
                location_intent=state.get("location_intent", LocationIntent()),
                category_intent=state.get("category_intent", CategoryIntent()),
                feature_intent=state.get("feature_intent", PetFeatureIntent()),
                quality_intent=state.get("quality_intent", QualityIntent()),
                time_intent=state.get("time_intent", TimeIntent()),
                distance_intent=state.get("distance_intent", DistanceIntent()),
            )
        },
    )

    graph.add_edge(START, "typo_normalizer")
    graph.add_edge("typo_normalizer", "router")
    graph.add_conditional_edges(
        "router",
        next_after_router,
        {"keyword": "keyword_plan", "semantic": "semantic_fanout"},
    )
    graph.add_edge("keyword_plan", END)
    graph.add_edge("semantic_fanout", "location_parser")
    graph.add_edge("semantic_fanout", "category_parser")
    graph.add_edge("semantic_fanout", "feature_parser")
    graph.add_edge("semantic_fanout", "quality_parser")
    graph.add_edge("semantic_fanout", "time_parser")
    graph.add_edge("semantic_fanout", "distance_parser")
    graph.add_edge("location_parser", "merge_plan")
    graph.add_edge("category_parser", "merge_plan")
    graph.add_edge("feature_parser", "merge_plan")
    graph.add_edge("quality_parser", "merge_plan")
    graph.add_edge("time_parser", "merge_plan")
    graph.add_edge("distance_parser", "merge_plan")
    graph.add_edge("merge_plan", "confidence_gate")
    graph.add_conditional_edges(
        "confidence_gate",
        next_after_gate,
        {"fallback": END, "semantic": END},
    )

    app = graph.compile()
    result = app.invoke({"raw_query": user_input, "query_text": user_input})
    return result["plan"]
