import pytest

from application.property import PropertyService
from domain.entities.search_v2 import SearchPlanV2
from domain.entities.property import PropertyFilterCondition
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.services.property_enrichment import IEnrichmentProvider


class DummyEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, plan: SearchPlanV2, geocode_result=("landmark", None)):
        self.plan = plan
        self.geocode_result = geocode_result

    def create_property_by_name(self, property_name: str):
        raise NotImplementedError

    def generate_ai_analysis(self, source):
        raise NotImplementedError

    def extract_search_criteria(self, query: str):
        raise NotImplementedError

    def extract_search_plan_v2(self, query: str) -> SearchPlanV2:
        return self.plan

    def geocode_landmark(self, landmark_name: str):
        return self.geocode_result


class CaptureRepo(IPropertyRepository):
    def __init__(self, query_items=None, keyword_items=None):
        self.query_items = query_items or []
        self.keyword_items = keyword_items or []
        self.calls = []

    async def find_by_query(self, query):
        self.calls.append(("find_by_query", query))
        return list(self.query_items)

    async def get_by_keyword(self, q):
        self.calls.append(("get_by_keyword", q))
        return list(self.keyword_items)

    async def get_nearby(self, lat, lng, radius, types, page, size):
        raise NotImplementedError

    async def get_property_by_id(self, property_id, include_deleted=False):
        raise NotImplementedError

    async def get_property_by_place_id(self, place_id, include_deleted=False):
        raise NotImplementedError

    async def get_properties_by_ids(self, property_ids):
        raise NotImplementedError

    async def create(self, new_property):
        raise NotImplementedError

    async def save(self, property_entity):
        raise NotImplementedError


class DummyRawDataRepo(IPlaceRawDataRepository):
    async def create(self, source):
        raise NotImplementedError

    async def save(self, source):
        raise NotImplementedError


class DummyAuditRepo(IPropertyAuditRepository):
    async def create(self, audit_log):
        return audit_log

    async def list_by_property_id(self, property_id, limit=50):
        return []


@pytest.mark.asyncio
async def test_search_by_keyword_v2_uses_keyword_route_directly(
    property_entity_factory,
):
    keyword_item = property_entity_factory(identifier="keyword-hit")
    repo = CaptureRepo(keyword_items=[keyword_item])
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=DummyAuditRepo(),
        enrichment_provider=DummyEnrichmentProvider(
            SearchPlanV2(route="keyword", route_reason="looks like a place name")
        ),
    )

    results, plan = await service.search_by_keyword_v2("肉球森林")

    assert [item.id for item in results] == ["keyword-hit"]
    assert plan.route == "keyword"
    assert repo.calls == [("get_by_keyword", "肉球森林")]


@pytest.mark.asyncio
async def test_search_by_keyword_v2_falls_back_when_semantic_plan_requests_it(
    property_entity_factory,
):
    keyword_item = property_entity_factory(identifier="fallback-hit")
    repo = CaptureRepo(keyword_items=[keyword_item])
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=DummyAuditRepo(),
        enrichment_provider=DummyEnrichmentProvider(
            SearchPlanV2(
                route="semantic",
                used_fallback=True,
                fallback_reason="low_confidence_primary_type",
                semantic_extraction={"category": "cafe"},
            )
        ),
    )

    results, plan = await service.search_by_keyword_v2("推薦的店")

    assert [item.id for item in results] == ["fallback-hit"]
    assert plan.used_fallback is True
    assert plan.fallback_reason == "low_confidence_primary_type"
    assert repo.calls == [("get_by_keyword", "推薦的店")]


@pytest.mark.asyncio
async def test_search_by_keyword_v2_returns_empty_when_semantic_query_has_no_results():
    repo = CaptureRepo(
        query_items=[],
    )
    plan = SearchPlanV2(
        route="semantic",
        filter_condition=PropertyFilterCondition(
            mongo_query={"primary_type": "cafe"},
            preferences=[{"key": "primary_type_preference", "label": "cafe"}],
        ),
        semantic_extraction={"category": "cafe"},
    )
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=DummyAuditRepo(),
        enrichment_provider=DummyEnrichmentProvider(plan),
    )

    results, updated_plan = await service.search_by_keyword_v2("咖啡廳")

    assert results == []
    assert updated_plan.used_fallback is False
    assert updated_plan.fallback_reason is None
    assert repo.calls == [("find_by_query", {"primary_type": "cafe"})]


def test_semantic_summary_and_query_ignore_false_feature_preferences():
    from domain.entities.search_v2 import (
        CategoryIntent,
        LocationIntent,
        PetFeatureIntent,
        QualityIntent,
        SearchRouteDecision,
    )
    from infrastructure.google.search_v2 import _merge_node

    result = _merge_node(
        {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.9,
                reason="has category",
            ),
            "location_intent": LocationIntent(
                kind="address", value="台北", confidence=0.9
            ),
            "category_intent": CategoryIntent(
                primary_type="restaurant",
                confidence=0.9,
            ),
            "feature_intent": PetFeatureIntent(
                features={
                    "pet_menu": True,
                    "free_water": False,
                    "allow_on_floor": False,
                },
                confidence=0.9,
            ),
            "quality_intent": QualityIntent(),
        }
    )

    plan = result["plan"]
    assert plan.filter_condition.mongo_query == {
        "address": {"$regex": "台北", "$options": "i"},
        "primary_type": "restaurant",
        "effective_pet_features.services.pet_menu": True,
    }
    assert plan.semantic_extraction == {
        "address": "台北",
        "category": "restaurant",
        "preferences": {"pet_menu": True},
    }
    assert [item["key"] for item in plan.filter_condition.preferences] == [
        "address_preference",
        "primary_type_preference",
        "pet_menu_preference",
    ]


def test_low_confidence_location_is_dropped_without_full_fallback():
    from domain.entities.search_v2 import (
        CategoryIntent,
        LocationIntent,
        PetFeatureIntent,
        QualityIntent,
        SearchRouteDecision,
    )
    from infrastructure.google.search_v2 import _confidence_gate_node, _merge_node

    merged = _merge_node(
        {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.9,
                reason="has category and area",
            ),
            "location_intent": LocationIntent(
                kind="address",
                value="台北",
                confidence=0.4,
            ),
            "category_intent": CategoryIntent(
                primary_type="restaurant",
                confidence=0.92,
            ),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.9),
            "quality_intent": QualityIntent(),
        }
    )

    result = _confidence_gate_node(
        {
            "plan": merged["plan"],
            "location_intent": LocationIntent(
                kind="address",
                value="台北",
                confidence=0.4,
            ),
            "category_intent": CategoryIntent(
                primary_type="restaurant",
                confidence=0.92,
            ),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.9),
            "quality_intent": QualityIntent(),
        }
    )

    plan = result["plan"]
    assert plan.used_fallback is False
    assert plan.fallback_reason is None
    assert plan.filter_condition.mongo_query == {"primary_type": "restaurant"}
    assert plan.semantic_extraction == {"category": "restaurant"}
    assert plan.warnings == ["low_confidence_location"]


def test_address_only_semantic_query_is_allowed_without_fallback():
    from domain.entities.search_v2 import (
        CategoryIntent,
        LocationIntent,
        PetFeatureIntent,
        QualityIntent,
        SearchRouteDecision,
    )
    from infrastructure.google.search_v2 import _confidence_gate_node, _merge_node

    merged = _merge_node(
        {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.95,
                reason="query is an address condition",
            ),
            "location_intent": LocationIntent(
                kind="address",
                value="台北",
                confidence=0.95,
            ),
            "category_intent": CategoryIntent(),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.0),
            "quality_intent": QualityIntent(),
        }
    )

    result = _confidence_gate_node(
        {
            "plan": merged["plan"],
            "location_intent": LocationIntent(
                kind="address",
                value="台北",
                confidence=0.95,
            ),
            "category_intent": CategoryIntent(),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.0),
            "quality_intent": QualityIntent(),
        }
    )

    plan = result["plan"]
    assert plan.used_fallback is False
    assert plan.fallback_reason is None
    assert plan.filter_condition.mongo_query == {
        "address": {"$regex": "台北", "$options": "i"}
    }
    assert plan.semantic_extraction == {"address": "台北"}


def test_low_confidence_primary_type_becomes_warning_not_fallback():
    from domain.entities.search_v2 import (
        CategoryIntent,
        LocationIntent,
        PetFeatureIntent,
        QualityIntent,
        SearchRouteDecision,
    )
    from infrastructure.google.search_v2 import _confidence_gate_node, _merge_node

    merged = _merge_node(
        {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.9,
                reason="has category",
            ),
            "location_intent": LocationIntent(
                kind="address", value="桃園", confidence=0.95
            ),
            "category_intent": CategoryIntent(
                primary_type="restaurant",
                confidence=0.45,
            ),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.9),
            "quality_intent": QualityIntent(),
        }
    )

    result = _confidence_gate_node(
        {
            "plan": merged["plan"],
            "location_intent": LocationIntent(
                kind="address", value="桃園", confidence=0.95
            ),
            "category_intent": CategoryIntent(
                primary_type="restaurant",
                confidence=0.45,
            ),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.9),
            "quality_intent": QualityIntent(),
        }
    )

    plan = result["plan"]
    assert plan.used_fallback is False
    assert plan.fallback_reason is None
    assert plan.filter_condition.mongo_query == {
        "address": {"$regex": "桃園", "$options": "i"},
        "primary_type": "restaurant",
    }
    assert plan.warnings == ["low_confidence_primary_type"]


def test_rule_based_location_parser_recognizes_taoyuan_as_address():
    from infrastructure.google.search_v2 import _extract_address_by_rule

    assert _extract_address_by_rule("台北") == "台北"
    assert _extract_address_by_rule("桃園 火鍋店") == "桃園"
    assert _extract_address_by_rule("中壢區 咖啡廳") == "中壢區"
    assert _extract_address_by_rule("中山路 寵物友善餐廳") == "中山路"


def test_route_node_treats_pure_address_query_as_semantic():
    from infrastructure.google.search_v2 import _route_node

    result = _route_node(llm=None, state={"raw_query": "台北"})

    assert result["route_decision"].route == "semantic"
    assert result["route_decision"].reason == "查詢本身就是行政區或地址條件"


def test_rule_based_landmark_parser_recognizes_sun_moon_lake():
    from infrastructure.google.search_v2 import (
        _extract_landmark_by_rule,
        _is_pure_landmark_query,
    )

    assert _extract_landmark_by_rule("日月潭") == "日月潭"
    assert _extract_landmark_by_rule("日月潭 咖啡廳") == "日月潭"
    assert _extract_landmark_by_rule("日月潭的民宿") == "日月潭"
    assert _extract_landmark_by_rule("日月潭附近") == "日月潭"
    assert _extract_landmark_by_rule("士林夜市") == "士林夜市"
    assert _is_pure_landmark_query("日月潭") is True
    assert _is_pure_landmark_query("日月潭 咖啡廳") is False


def test_category_node_returns_empty_for_pure_landmark_query():
    from infrastructure.google.search_v2 import _category_node

    result = _category_node(llm=None, state={"raw_query": "日月潭"})

    assert result["category_intent"].primary_type is None
    assert result["category_intent"].category_key is None


def test_category_node_returns_empty_for_landmark_nearby_query():
    from infrastructure.google.search_v2 import _category_node

    result = _category_node(llm=None, state={"raw_query": "日月潭附近"})

    assert result["category_intent"].primary_type is None
    assert result["category_intent"].category_key is None


def test_feature_node_skips_llm_when_query_has_no_feature_hints():
    from infrastructure.google.search_v2 import _feature_node

    result = _feature_node(llm=None, state={"raw_query": "台北"})

    assert result["feature_intent"].features == {}


def test_feature_node_uses_rule_based_pet_menu_hint():
    from infrastructure.google.search_v2 import _feature_node

    result = _feature_node(llm=None, state={"raw_query": "有寵物餐的咖啡廳"})

    assert result["feature_intent"].features == {"pet_menu": True}


def test_quality_node_skips_llm_when_query_has_no_quality_hints():
    from infrastructure.google.search_v2 import _quality_node

    result = _quality_node(llm=None, state={"raw_query": "日月潭附近"})

    assert result["quality_intent"].min_rating is None
    assert result["quality_intent"].is_open is None


def test_quality_node_uses_rule_based_open_now_hint():
    from infrastructure.google.search_v2 import _quality_node

    result = _quality_node(llm=None, state={"raw_query": "現在有開的咖啡廳"})

    assert result["quality_intent"].is_open is True


def test_route_node_treats_rule_based_landmark_query_as_semantic():
    from infrastructure.google.search_v2 import _route_node

    result = _route_node(llm=None, state={"raw_query": "日月潭"})

    assert result["route_decision"].route == "semantic"
    assert result["route_decision"].reason == "查詢本身就是地標條件"
    assert result["location_intent"].kind == "landmark"
    assert result["location_intent"].value == "日月潭"


def test_route_node_treats_pure_landmark_query_as_semantic(monkeypatch):
    from domain.entities.search_v2 import LocationIntent
    from infrastructure.google import search_v2

    def fake_invoke_structured(
        llm,
        system_prompt,
        user_input,
        schema,
        extra_variables=None,
    ):
        if schema is LocationIntent:
            return LocationIntent(
                kind="landmark",
                value="日月潭",
                confidence=0.92,
                evidence="matched landmark by llm",
            )
        raise AssertionError(
            "router prompt should not be invoked for pure landmark query"
        )

    monkeypatch.setattr(search_v2, "_invoke_structured", fake_invoke_structured)

    result = search_v2._route_node(llm=object(), state={"raw_query": "日月潭"})

    assert result["route_decision"].route == "semantic"
    assert result["route_decision"].reason == "查詢本身就是地標條件"
    assert result["location_intent"].kind == "landmark"
    assert result["location_intent"].value == "日月潭"


def test_route_node_prefers_rule_based_landmark_before_llm(monkeypatch):
    from infrastructure.google import search_v2

    def fake_invoke_structured(*args, **kwargs):
        raise AssertionError("llm should not be invoked for rule-based landmark query")

    monkeypatch.setattr(search_v2, "_invoke_structured", fake_invoke_structured)

    result = search_v2._route_node(llm=object(), state={"raw_query": "日月潭"})

    assert result["route_decision"].route == "semantic"
    assert result["route_decision"].reason == "查詢本身就是地標條件"
    assert result["location_intent"].kind == "landmark"
    assert result["location_intent"].value == "日月潭"


def test_rule_based_category_parser_recognizes_hot_pot_as_primary_type():
    from infrastructure.google.search_v2 import _extract_category_by_rule

    intent = _extract_category_by_rule("桃園 火鍋店")

    assert intent is not None
    assert intent.primary_type == "hot_pot_restaurant"
    assert intent.matched_from == "primary_type"


def test_comma_separated_primary_type_is_normalized_by_query_rule():
    from domain.entities.search_v2 import CategoryIntent
    from infrastructure.google.search_v2 import _normalize_category_intent

    intent = _normalize_category_intent(
        "桃園 火鍋店",
        CategoryIntent(
            primary_type="hot_pot_restaurant,restaurant,chinese_restaurant",
            matched_from="primary_type",
            confidence=0.6,
        ),
    )

    assert intent.primary_type == "hot_pot_restaurant"
    assert intent.matched_from == "primary_type"


def test_category_match_expands_to_primary_type_list():
    from domain.entities.property_category import PropertyCategoryKey
    from domain.entities.search_v2 import (
        CategoryIntent,
        LocationIntent,
        PetFeatureIntent,
        QualityIntent,
        SearchRouteDecision,
    )
    from infrastructure.google.search_v2 import _merge_node

    result = _merge_node(
        {
            "route_decision": SearchRouteDecision(
                route="semantic",
                confidence=0.9,
                reason="matched category",
            ),
            "location_intent": LocationIntent(),
            "category_intent": CategoryIntent(
                category_key=PropertyCategoryKey.RESTAURANT,
                matched_from="category",
                confidence=0.9,
                evidence="matched category restaurant",
            ),
            "feature_intent": PetFeatureIntent(features={}, confidence=0.9),
            "quality_intent": QualityIntent(),
        }
    )

    plan = result["plan"]
    assert "primary_type" in plan.filter_condition.mongo_query
    assert "$in" in plan.filter_condition.mongo_query["primary_type"]
    assert "restaurant" in plan.filter_condition.mongo_query["primary_type"]["$in"]
    assert (
        "hot_pot_restaurant" in plan.filter_condition.mongo_query["primary_type"]["$in"]
    )
    assert plan.semantic_extraction == {"category": "restaurant"}
    assert plan.filter_condition.preferences == [
        {"key": "category_preference", "label": "restaurant"}
    ]


def test_category_prompt_uses_dynamic_property_categories_variable():
    from infrastructure.prompt.search_v2 import CATEGORY_PARSER_PROMPT

    assert "{property_categories}" in CATEGORY_PARSER_PROMPT
