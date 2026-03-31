import re
import json
from typing import Any, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph

from domain.entities.property import PropertyEntity, PropertyFilterCondition
from domain.entities.property_category import (
    PropertyCategoryKey,
    PROPERTY_CATEGORIES,
    get_primary_types_by_category_key,
)
from domain.entities.search import (
    CategoryIntent,
    DistanceIntent,
    LocationIntent,
    PetFeatureIntent,
    QualityIntent,
    SearchPlan,
    SearchRouteDecision,
    TypoCorrectionIntent,
)
from infrastructure.prompt import (
    CATEGORY_PARSER_PROMPT,
    FEATURE_PARSER_PROMPT,
    LOCATION_PARSER_PROMPT,
    QUALITY_PARSER_PROMPT,
    ROUTER_PROMPT,
    TYPO_NORMALIZER_PROMPT,
)


FEATURE_FIELD_MAP = {
    "leash_required": "effective_pet_features.rules.leash_required",
    "stroller_required": "effective_pet_features.rules.stroller_required",
    "allow_on_floor": "effective_pet_features.rules.allow_on_floor",
    "stairs": "effective_pet_features.environment.stairs",
    "outdoor_seating": "effective_pet_features.environment.outdoor_seating",
    "spacious": "effective_pet_features.environment.spacious",
    "indoor_ac": "effective_pet_features.environment.indoor_ac",
    "off_leash_possible": "effective_pet_features.environment.off_leash_possible",
    "pet_friendly_floor": "effective_pet_features.environment.pet_friendly_floor",
    "has_shop_pet": "effective_pet_features.environment.has_shop_pet",
    "pet_menu": "effective_pet_features.services.pet_menu",
    "free_water": "effective_pet_features.services.free_water",
    "free_treats": "effective_pet_features.services.free_treats",
    "pet_seating": "effective_pet_features.services.pet_seating",
}

TAIWAN_ADDRESS_KEYWORDS = [
    "台北",
    "臺北",
    "新北",
    "桃園",
    "台中",
    "臺中",
    "台南",
    "臺南",
    "高雄",
    "基隆",
    "新竹",
    "苗栗",
    "彰化",
    "南投",
    "雲林",
    "嘉義",
    "屏東",
    "宜蘭",
    "花蓮",
    "台東",
    "臺東",
    "澎湖",
    "金門",
    "連江",
]
ADDRESS_SUFFIX_PATTERN = re.compile(
    r"(?P<value>[^\s,，。]{1,12}(?:縣|市|區|鄉|鎮|村|里|路|街|大道|段|巷|弄))"
)

RULE_BASED_PRIMARY_TYPE_KEYWORDS = [
    ("火鍋", "hot_pot_restaurant"),
    ("燒肉", "yakiniku_restaurant"),
    ("烤肉", "yakiniku_restaurant"),
    ("拉麵", "ramen_restaurant"),
    ("早午餐", "brunch_restaurant"),
    ("餐酒館", "bistro"),
    ("獸醫", "veterinary_care"),
    ("看醫生", "veterinary_care"),
    ("寵物美容", "pet_care"),
    ("洗澡", "pet_care"),
    ("剪毛", "pet_care"),
    ("美容", "pet_care"),
    ("寵物用品", "pet_store"),
]

RULE_BASED_CATEGORY_KEYWORDS = [
    ("咖啡廳", PropertyCategoryKey.CAFE),
    ("咖啡店", PropertyCategoryKey.CAFE),
    ("下午茶", PropertyCategoryKey.CAFE),
    ("甜點", PropertyCategoryKey.CAFE),
    ("餐廳", PropertyCategoryKey.RESTAURANT),
    ("美食", PropertyCategoryKey.RESTAURANT),
    ("公園", PropertyCategoryKey.OUTDOOR),
    ("戶外", PropertyCategoryKey.OUTDOOR),
    ("住宿", PropertyCategoryKey.LODGING),
    ("民宿", PropertyCategoryKey.LODGING),
    ("旅館", PropertyCategoryKey.LODGING),
]

RULE_BASED_LANDMARK_KEYWORDS = [
    "台北101",
    "日月潭",
    "阿里山",
    "太魯閣",
    "清境農場",
    "陽明山",
    "九份",
    "十分",
    "野柳",
    "墾丁",
]

RULE_BASED_LANDMARK_SUFFIXES = (
    "夜市",
    "老街",
    "車站",
    "機場",
    "漁港",
    "碼頭",
    "百貨",
    "名品城",
    "美術館",
    "博物館",
    "動物園",
    "植物園",
    "風景區",
    "國家公園",
    "森林遊樂區",
    "遊樂區",
    "遊樂園",
)

FEATURE_HINT_KEYWORDS = {
    "leash_required": ("牽繩",),
    "stroller_required": ("推車", "提籠"),
    "allow_on_floor": ("可落地", "落地"),
    "stairs": ("樓梯",),
    "outdoor_seating": ("戶外", "露天", "戶外座位"),
    "spacious": ("空間大", "寬敞"),
    "indoor_ac": ("冷氣", "空調"),
    "off_leash_possible": ("放繩", "奔跑"),
    "pet_friendly_floor": ("止滑", "地墊"),
    "has_shop_pet": ("有店狗", "有店貓", "店裡有狗"),
    "pet_menu": ("寵物餐",),
    "free_water": ("水碗", "飲水", "有水"),
    "free_treats": ("零食", "點心"),
    "pet_seating": ("上椅", "一起坐", "座位"),
}

NEGATIVE_FEATURE_HINT_KEYWORDS = {
    "stroller_required": ("不用推車", "免推車", "不用提籠", "免提籠"),
    "allow_on_floor": ("不可落地", "不能落地"),
    "has_shop_pet": ("沒有店狗",)
}

QUALITY_HINT_KEYWORDS = {
    "min_rating": ("推薦", "評價", "熱門", "最好", "頂級"),
    "is_open": ("現在有開", "營業中", "現在營業", "開著", "不想白跑", "有開", "有開的"),
}

TRANSPORT_SPEED_KMH = {
    "driving": 50,
    "bicycling": 15,
    "walking": 5,
}
TRANSPORT_DISTANCE_DISCOUNT = {
    "driving": 0.9,
    "bicycling": 0.9,
    "walking": 0.9,
}
TRANSPORT_LABELS = {
    "driving": "車程",
    "bicycling": "騎車",
    "walking": "步行",
}
TRANSPORT_KEYWORDS = {
    "walking": ("步行", "走路", "徒步"),
    "bicycling": ("騎車", "單車", "自行車", "腳踏車", "騎腳踏車"),
    "driving": ("開車", "車程"),
}
TRAVEL_TIME_PATTERN = re.compile(
    r"(?:距離\s*)?(?:(?P<prefix_mode>步行|走路|徒步|騎車|單車|自行車|腳踏車|騎腳踏車|開車|車程)\s*)?(?P<minutes>\d{1,3})\s*分鐘(?:\s*(?P<suffix_mode>步行|走路|徒步|騎車|單車|自行車|腳踏車|騎腳踏車|開車|車程|內))?"
)

NON_SEARCH_EXACT_QUERIES = {
    "你好",
    "哈囉",
    "嗨",
    "謝謝",
    "感謝",
    "你是誰",
    "你會什麼",
    "你可以做什麼",
}

NON_SEARCH_PHRASES = (
    "幫我分析",
    "幫我看",
    "你看一下",
    "這是什麼",
    "怎麼用",
    "怎麼做",
)

PROMPT_INJECTION_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your prompt",
    "忽略之前",
    "忽略前面",
    "忽略以上",
    "忘掉之前",
    "系統提示",
    "系統 prompt",
    "開發者訊息",
    "developer prompt",
    "你現在是",
    "請扮演",
    "roleplay as",
    "act as",
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
    distance_intent: DistanceIntent
    plan: SearchPlan


def _invoke_structured(
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


def _normalize_text_for_match(value: str) -> str:
    return re.sub(r"\s+", "", value).strip()


def _current_query(state: SearchGraphState) -> str:
    return state.get("query_text") or state["raw_query"]


def _is_basic_prompt_injection(query: str) -> bool:
    normalized_query = query.lower()
    return any(pattern in normalized_query for pattern in PROMPT_INJECTION_PATTERNS)


def _is_obviously_non_search_query(query: str) -> bool:
    normalized_query = _normalize_text_for_match(query)
    if not normalized_query:
        return True

    if _is_basic_prompt_injection(query):
        return False

    if normalized_query in {
        _normalize_text_for_match(item) for item in NON_SEARCH_EXACT_QUERIES
    }:
        return True

    if any(phrase in query for phrase in NON_SEARCH_PHRASES):
        return True

    if _extract_address_by_rule(query):
        return False

    if _extract_landmark_by_rule(query):
        return False

    if _extract_category_by_rule(query):
        return False

    if _extract_feature_by_rule(query) or _extract_quality_by_rule(query):
        return False

    if any(keyword in query for keyword in ("找", "搜尋", "附近")):
        return False

    if query.endswith(("嗎", "呢", "？", "?")):
        return True

    return False


def _extract_landmark_by_rule(query: str) -> str | None:
    normalized_query = _normalize_text_for_match(query)
    if not normalized_query:
        return None

    for keyword in sorted(RULE_BASED_LANDMARK_KEYWORDS, key=len, reverse=True):
        normalized_keyword = _normalize_text_for_match(keyword)
        if normalized_keyword in normalized_query:
            return keyword

    if any(
        normalized_query.endswith(suffix) for suffix in RULE_BASED_LANDMARK_SUFFIXES
    ):
        return query.strip()

    if (
        normalized_query[-1:] in {"潭", "湖", "山", "溪", "島"}
        and len(normalized_query) <= 6
    ):
        return query.strip()

    return None


def _is_pure_landmark_query(query: str) -> bool:
    landmark = _extract_landmark_by_rule(query)
    if not landmark:
        return False

    normalized_query = _normalize_text_for_match(query)
    normalized_landmark = _normalize_text_for_match(landmark)
    if normalized_query != normalized_landmark:
        return False

    return _extract_category_by_rule(query) is None


def _has_feature_hints(query: str) -> bool:
    return any(
        keyword in query
        for keywords in FEATURE_HINT_KEYWORDS.values()
        for keyword in keywords
    ) or any(
        keyword in query
        for keywords in NEGATIVE_FEATURE_HINT_KEYWORDS.values()
        for keyword in keywords
    )


def _extract_feature_by_rule(query: str) -> PetFeatureIntent | None:
    if not _has_feature_hints(query):
        return None

    features: dict[str, bool] = {}
    matched_keywords: list[str] = []

    for feature_name, keywords in FEATURE_HINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                features[feature_name] = True
                matched_keywords.append(keyword)
                break

    for feature_name, keywords in NEGATIVE_FEATURE_HINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                features[feature_name] = False
                matched_keywords.append(keyword)
                break

    if not features:
        return None

    return PetFeatureIntent(
        features=features,
        confidence=0.98,
        evidence=f"matched pet feature keywords by rule: {', '.join(matched_keywords)}",
    )


def _has_quality_hints(query: str) -> bool:
    return any(
        keyword in query
        for keywords in QUALITY_HINT_KEYWORDS.values()
        for keyword in keywords
    )


def _extract_quality_by_rule(query: str) -> QualityIntent | None:
    if not _has_quality_hints(query):
        return None

    min_rating = None
    is_open = None
    matched_keywords: list[str] = []

    if any(keyword in query for keyword in ("最好", "頂級")):
        min_rating = 4.0
        matched_keywords.extend(
            [keyword for keyword in ("最好", "頂級") if keyword in query]
        )
    elif any(keyword in query for keyword in ("推薦", "評價", "熱門")):
        min_rating = 3.8
        matched_keywords.extend(
            [keyword for keyword in ("推薦", "評價", "熱門") if keyword in query]
        )

    if any(keyword in query for keyword in QUALITY_HINT_KEYWORDS["is_open"]):
        is_open = True
        matched_keywords.extend(
            [
                keyword
                for keyword in QUALITY_HINT_KEYWORDS["is_open"]
                if keyword in query
            ]
        )

    return QualityIntent(
        min_rating=min_rating,
        is_open=is_open,
        confidence=0.98,
        evidence=f"matched quality keywords by rule: {', '.join(dict.fromkeys(matched_keywords))}",
    )


def _should_run_typo_normalizer(query: str) -> bool:
    normalized_query = _normalize_text_for_match(query)
    if not normalized_query or len(normalized_query) < 2:
        return False

    if _is_basic_prompt_injection(query):
        return False

    if _is_obviously_non_search_query(query):
        return False

    if _extract_landmark_by_rule(query):
        return False

    if _extract_category_by_rule(query):
        return False

    if _extract_feature_by_rule(query) or _extract_quality_by_rule(query):
        return False

    rule_based_address = _extract_address_by_rule(query)
    if rule_based_address:
        remaining_query = query.replace(rule_based_address, "").strip()
        return bool(remaining_query)

    return False


def _typo_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = _current_query(state)
    if not _should_run_typo_normalizer(query):
        return {
            "query_text": query,
            "typo_intent": TypoCorrectionIntent(
                corrected_query=query,
                changed=False,
                confidence=1.0,
                evidence="skip typo normalization by heuristic",
            ),
        }

    intent = _invoke_structured(
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

    return {
        "query_text": corrected_query,
        "typo_intent": intent,
    }


def _route_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = _current_query(state)
    if _is_basic_prompt_injection(query):
        return {
            "route_decision": SearchRouteDecision(
                route="keyword",
                confidence=0.99,
                reason="查詢包含 prompt injection 訊號，改用關鍵字搜尋",
            )
        }

    if _is_obviously_non_search_query(query):
        return {
            "route_decision": SearchRouteDecision(
                route="keyword",
                confidence=0.98,
                reason="查詢內容不像搜尋條件，改用關鍵字搜尋",
            )
        }

    rule_based_address = _extract_address_by_rule(query)
    rule_based_category = _extract_category_by_rule(query)
    rule_based_feature = _extract_feature_by_rule(query)
    rule_based_quality = _extract_quality_by_rule(query)
    rule_based_distance = _extract_distance_by_rule(query)
    normalized_query = _normalize_text_for_match(query)
    if rule_based_address and normalized_query == rule_based_address:
        return {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.98,
                reason="查詢本身就是行政區或地址條件",
            )
        }

    if rule_based_address and rule_based_category:
        return {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.98,
                reason="包含地點和分類條件",
            )
        }

    rule_based_landmark = _extract_landmark_by_rule(query)
    if rule_based_landmark:
        return {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.98,
                reason="查詢本身就是地標條件",
            ),
            "location_intent": LocationIntent(
                kind="landmark",
                value=rule_based_landmark,
                confidence=0.98,
                evidence="matched landmark keyword or suffix by rule",
            ),
        }

    if (
        rule_based_category
        or rule_based_feature
        or rule_based_quality
        or rule_based_distance
        or _should_use_current_location_context(query)
    ):
        return {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.95,
                reason="查詢包含分類或偏好條件",
            )
        }

    entity_schema = PropertyEntity.model_json_schema()
    location_intent = _invoke_structured(
        llm=llm,
        system_prompt=LOCATION_PARSER_PROMPT,
        user_input=query,
        schema=LocationIntent,
        extra_variables={"entity_schema": str(entity_schema)},
    )
    normalized_landmark = _normalize_text_for_match(location_intent.value or "")
    if (
        location_intent.kind == "landmark"
        and location_intent.value
        and (
            normalized_query in normalized_landmark
            or normalized_landmark in normalized_query
        )
        and location_intent.confidence >= 0.7
    ):
        return {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=location_intent.confidence,
                reason="查詢本身就是地標條件",
            ),
            "location_intent": location_intent,
        }

    decision = _invoke_structured(
        llm=llm,
        system_prompt=ROUTER_PROMPT,
        user_input=query,
        schema=SearchRouteDecision,
    )
    return {"route_decision": decision}


def _extract_address_by_rule(query: str) -> str | None:
    rule_based_landmark = _extract_landmark_by_rule(query)

    for keyword in sorted(TAIWAN_ADDRESS_KEYWORDS, key=len, reverse=True):
        if keyword in query:
            if (
                rule_based_landmark
                and keyword in rule_based_landmark
                and len(keyword) < len(rule_based_landmark)
            ):
                continue
            return keyword

    match = ADDRESS_SUFFIX_PATTERN.search(query)
    if match:
        return match.group("value")

    return None


def _extract_category_by_rule(query: str) -> CategoryIntent | None:
    for keyword, primary_type in RULE_BASED_PRIMARY_TYPE_KEYWORDS:
        if keyword in query:
            return CategoryIntent(
                primary_type=primary_type,
                matched_from="primary_type",
                confidence=0.95,
                evidence=f"matched primary type keyword by rule: {keyword}",
            )

    for keyword, category_key in RULE_BASED_CATEGORY_KEYWORDS:
        if keyword in query:
            return CategoryIntent(
                category_key=category_key,
                matched_from="category",
                confidence=0.95,
                evidence=f"matched category keyword by rule: {keyword}",
            )

    return None


def _should_use_current_location_context(query: str) -> bool:
    if not TRAVEL_TIME_PATTERN.search(query):
        return False

    if _extract_address_by_rule(query):
        return False

    if _extract_landmark_by_rule(query):
        return False

    return True


def _normalize_category_intent(query: str, intent: CategoryIntent) -> CategoryIntent:
    if intent.primary_type and "," in intent.primary_type:
        rule_based = _extract_category_by_rule(query)
        if rule_based:
            return rule_based

        raw_values = [
            item.strip() for item in intent.primary_type.split(",") if item.strip()
        ]
        unique_values = list(dict.fromkeys(raw_values))
        for category in PROPERTY_CATEGORIES:
            category_set = set(category.primary_types)
            if set(unique_values).issubset(category_set):
                return CategoryIntent(
                    category_key=category.key,
                    matched_from="category",
                    confidence=intent.confidence,
                    evidence="normalized comma-separated primary_type output into category",
                )
        if unique_values:
            return CategoryIntent(
                primary_type=unique_values[0],
                matched_from="primary_type",
                confidence=intent.confidence,
                evidence="normalized comma-separated primary_type output into first candidate",
            )

    return intent


def _semantic_fanout_node(state: SearchGraphState) -> SearchGraphState:
    return state


def _location_node(llm, state: SearchGraphState) -> dict[str, Any]:
    existing_intent = state.get("location_intent")
    if existing_intent and existing_intent.kind != "none" and existing_intent.value:
        return {"location_intent": existing_intent}

    query = _current_query(state)
    rule_based_address = _extract_address_by_rule(query)
    if rule_based_address:
        return {
            "location_intent": LocationIntent(
                kind="address",
                value=rule_based_address,
                confidence=0.95,
                evidence="matched Taiwan administrative area or address suffix by rule",
            )
        }

    rule_based_landmark = _extract_landmark_by_rule(query)
    if rule_based_landmark:
        return {
            "location_intent": LocationIntent(
                kind="landmark",
                value=rule_based_landmark,
                confidence=0.98,
                evidence="matched landmark keyword or suffix by rule",
            )
        }

    if _should_use_current_location_context(query):
        return {
            "location_intent": LocationIntent(
                kind="landmark",
                value="CURRENT_LOCATION",
                confidence=0.95,
                evidence="travel-time query without explicit geo anchor defaults to CURRENT_LOCATION",
            )
        }

    if (
        _extract_category_by_rule(query)
        or _extract_feature_by_rule(query)
        or _extract_quality_by_rule(query)
        or _extract_distance_by_rule(query)
    ):
        return {"location_intent": LocationIntent()}

    entity_schema = PropertyEntity.model_json_schema()
    intent = _invoke_structured(
        llm=llm,
        system_prompt=LOCATION_PARSER_PROMPT,
        user_input=query,
        schema=LocationIntent,
        extra_variables={"entity_schema": str(entity_schema)},
    )
    return {"location_intent": intent}


def _category_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = _current_query(state)
    rule_based_landmark = _extract_landmark_by_rule(query)
    rule_based_intent = _extract_category_by_rule(query)
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
    intent = _invoke_structured(
        llm=llm,
        system_prompt=CATEGORY_PARSER_PROMPT,
        user_input=query,
        schema=CategoryIntent,
        extra_variables={"property_categories": property_categories},
    )
    return {"category_intent": _normalize_category_intent(query, intent)}


def _feature_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = _current_query(state)
    rule_based_intent = _extract_feature_by_rule(query)
    if rule_based_intent:
        return {"feature_intent": rule_based_intent}

    if not _has_feature_hints(query):
        return {"feature_intent": PetFeatureIntent()}

    intent = _invoke_structured(
        llm=llm,
        system_prompt=FEATURE_PARSER_PROMPT,
        user_input=query,
        schema=PetFeatureIntent,
    )
    return {"feature_intent": intent}


def _quality_node(llm, state: SearchGraphState) -> dict[str, Any]:
    query = _current_query(state)
    rule_based_intent = _extract_quality_by_rule(query)
    if rule_based_intent:
        return {"quality_intent": rule_based_intent}

    if not _has_quality_hints(query):
        return {"quality_intent": QualityIntent()}

    intent = _invoke_structured(
        llm=llm,
        system_prompt=QUALITY_PARSER_PROMPT,
        user_input=query,
        schema=QualityIntent,
    )
    return {"quality_intent": intent}


def _detect_transport_mode(query: str, matched_mode: str | None = None) -> str:
    if matched_mode:
        for mode, keywords in TRANSPORT_KEYWORDS.items():
            if matched_mode in keywords:
                return mode

    for mode, keywords in TRANSPORT_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
            return mode

    return "driving"


def _travel_minutes_to_radius_meters(minutes: int, transport_mode: str) -> int:
    distance_km = (
        TRANSPORT_SPEED_KMH[transport_mode]
        * (minutes / 60)
        * TRANSPORT_DISTANCE_DISCOUNT[transport_mode]
    )
    return int(distance_km * 1000)


def _extract_distance_by_rule(query: str) -> DistanceIntent | None:
    match = TRAVEL_TIME_PATTERN.search(query)
    if not match:
        return None

    minutes = int(match.group("minutes"))
    if minutes <= 0:
        return None

    transport_mode = _detect_transport_mode(
        query,
        matched_mode=match.group("prefix_mode") or match.group("suffix_mode"),
    )
    speed_kmh = TRANSPORT_SPEED_KMH[transport_mode]
    discount = TRANSPORT_DISTANCE_DISCOUNT[transport_mode]

    return DistanceIntent(
        transport_mode=transport_mode,
        travel_time_limit_min=minutes,
        search_radius_meters=_travel_minutes_to_radius_meters(minutes, transport_mode),
        confidence=0.95,
        evidence=(
            "converted travel time to radius by rule "
            f"({transport_mode} {speed_kmh}km/h * {minutes}min * {discount})"
        ),
    )


def _distance_node(state: SearchGraphState) -> dict[str, Any]:
    query = _current_query(state)
    rule_based_intent = _extract_distance_by_rule(query)
    if rule_based_intent:
        return {"distance_intent": rule_based_intent}

    return {"distance_intent": DistanceIntent()}


def _build_semantic_summary(
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


def _merge_node(state: SearchGraphState) -> dict[str, Any]:
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
        preferences.append(
            {"key": "address_preference", "label": location_intent.value}
        )

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
        semantic_extraction=_build_semantic_summary(
            location_intent=location_intent,
            category_intent=category_intent,
            feature_intent=feature_intent,
            quality_intent=quality_intent,
            distance_intent=distance_intent,
        ),
    )
    return {"plan": plan}


def _confidence_gate_node(state: SearchGraphState) -> dict[str, Any]:
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
        and quality_intent.is_open is None
        and quality_intent.min_rating is None
        and distance_intent.travel_time_limit_min is None
    ):
        fallback_reason = "semantic_parse_missing_core_constraints"

    # Low-confidence location should not block semantic retrieval entirely.
    # Instead, strip the location-derived constraint and continue with the
    # remaining high-confidence filters.
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


def _keyword_plan_node(state: SearchGraphState) -> dict[str, Any]:
    decision = state["route_decision"]
    plan = SearchPlan(
        route="keyword",
        route_reason=decision.reason,
        route_confidence=decision.confidence,
        filter_condition=PropertyFilterCondition(explanation=decision.reason),
    )
    return {"plan": plan}


def _next_after_router(state: SearchGraphState) -> str:
    return state["route_decision"].route


def _next_after_gate(state: SearchGraphState) -> str:
    return "fallback" if state["plan"].used_fallback else "semantic"


def extract_search_plan(llm, user_input: str) -> SearchPlan:
    graph = StateGraph(SearchGraphState)
    graph.add_node("typo_normalizer", lambda state: _typo_node(llm, state))
    graph.add_node("router", lambda state: _route_node(llm, state))
    graph.add_node("keyword_plan", _keyword_plan_node)
    graph.add_node("semantic_fanout", _semantic_fanout_node)
    graph.add_node("location_parser", lambda state: _location_node(llm, state))
    graph.add_node("category_parser", lambda state: _category_node(llm, state))
    graph.add_node("feature_parser", lambda state: _feature_node(llm, state))
    graph.add_node("quality_parser", lambda state: _quality_node(llm, state))
    graph.add_node("distance_parser", _distance_node)
    graph.add_node("merge_plan", _merge_node)
    graph.add_node("confidence_gate", _confidence_gate_node)

    graph.add_edge(START, "typo_normalizer")
    graph.add_edge("typo_normalizer", "router")
    graph.add_conditional_edges(
        "router",
        _next_after_router,
        {"keyword": "keyword_plan", "semantic": "semantic_fanout"},
    )
    graph.add_edge("keyword_plan", END)
    graph.add_edge("semantic_fanout", "location_parser")
    graph.add_edge("semantic_fanout", "category_parser")
    graph.add_edge("semantic_fanout", "feature_parser")
    graph.add_edge("semantic_fanout", "quality_parser")
    graph.add_edge("semantic_fanout", "distance_parser")
    graph.add_edge("location_parser", "merge_plan")
    graph.add_edge("category_parser", "merge_plan")
    graph.add_edge("feature_parser", "merge_plan")
    graph.add_edge("quality_parser", "merge_plan")
    graph.add_edge("distance_parser", "merge_plan")
    graph.add_edge("merge_plan", "confidence_gate")
    graph.add_conditional_edges(
        "confidence_gate",
        _next_after_gate,
        {"fallback": END, "semantic": END},
    )

    app = graph.compile()
    result = app.invoke({"raw_query": user_input, "query_text": user_input})
    return result["plan"]
