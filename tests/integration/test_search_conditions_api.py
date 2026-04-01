import pytest

from application.property import PropertyService
from domain.entities.search import SearchPlan
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.repositories.property_note import IPropertyNoteRepository
from domain.services.property_enrichment import IEnrichmentProvider
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import get_optional_current_user
from tests.integration.search_cases import SEARCH_CONDITION_CASES, SearchConditionCase


class CaptureQueryRepo(IPropertyRepository):
    def __init__(self):
        self.calls = []

    async def find_by_query(self, query, open_at_minutes=None):
        self.calls.append(("find_by_query", query, open_at_minutes))
        return []

    async def get_by_keyword(self, q):
        self.calls.append(("get_by_keyword", q))
        return []

    async def get_nearby(self, lat, lng, radius, types, page, size):
        raise NotImplementedError

    async def get_property_by_id(self, property_id, include_deleted=False):
        raise NotImplementedError

    async def get_property_by_place_id(self, place_id, include_deleted=False):
        raise NotImplementedError

    async def get_properties_by_ids(self, property_ids):
        return []

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


class DummyNoteRepo(IPropertyNoteRepository):
    async def get_by_user_and_property(self, user_id: str, property_id: str):
        return None

    async def upsert(self, user_id: str, property_id: str, content: str):
        raise NotImplementedError

    async def delete(self, user_id: str, property_id: str) -> bool:
        raise NotImplementedError

    async def list_by_user(self, user_id: str, page: int, size: int, query: str | None = None):
        raise NotImplementedError

    async def get_noted_property_ids(self, user_id: str, property_ids: list[str]) -> set[str]:
        return set()


class _NoopStructuredLLM:
    def with_structured_output(self, schema):
        raise AssertionError(
            "integration search condition tests should stay on the rule-based langgraph path"
        )


class LangGraphEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, geocode_map=None):
        self.last_plan: SearchPlan | None = None
        self.geocode_map = geocode_map or {}
        self.llm = _NoopStructuredLLM()

    def create_property_by_name(self, property_name: str):
        raise NotImplementedError

    def generate_ai_analysis(self, source):
        raise NotImplementedError

    def extract_search_plan(self, query: str) -> SearchPlan:
        from infrastructure.search.pipeline import extract_search_plan

        self.last_plan = extract_search_plan(self.llm, query)
        return self.last_plan

    def geocode_landmark(self, landmark_name: str):
        return landmark_name, self.geocode_map.get(landmark_name)


@pytest.fixture
def integration_search_setup(api_app):
    repo = CaptureQueryRepo()
    provider = LangGraphEnrichmentProvider(
        geocode_map={
            "台北101": (121.5645, 25.0339),
            "青埔": (121.2141, 25.0086),
        }
    )
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=DummyAuditRepo(),
        note_repo=DummyNoteRepo(),
        enrichment_provider=provider,
    )

    async def _property_service_override():
        return service

    async def _optional_user_override():
        return None

    api_app.dependency_overrides[get_property_service] = _property_service_override
    api_app.dependency_overrides[get_optional_current_user] = _optional_user_override

    yield repo, provider

    api_app.dependency_overrides.pop(get_property_service, None)
    api_app.dependency_overrides.pop(get_optional_current_user, None)

def _assert_mongo_query_matches_case(mongo_query: dict, case: SearchConditionCase) -> None:
    if case.query_checks.max_distance is not None:
        assert mongo_query["location"]["$nearSphere"]["$maxDistance"] == case.query_checks.max_distance

    if case.query_checks.primary_type_includes is not None:
        primary_type_query = mongo_query["primary_type"]
        if isinstance(primary_type_query, dict):
            assert case.query_checks.primary_type_includes in primary_type_query["$in"]
        else:
            assert primary_type_query == case.query_checks.primary_type_includes

    if case.query_checks.address_regex is not None:
        assert mongo_query["address"]["$regex"] == case.query_checks.address_regex

    if case.query_checks.is_open is not None:
        assert mongo_query["is_open"] is case.query_checks.is_open

    for field_name, field_value in case.query_checks.feature_equals.items():
        assert mongo_query[field_name] is field_value


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    SEARCH_CONDITION_CASES,
    ids=[case.query for case in SEARCH_CONDITION_CASES],
)
def test_search_api_exposes_expected_langgraph_conditions(
    client,
    integration_search_setup,
    case: SearchConditionCase,
):
    repo, provider = integration_search_setup

    response = client.get("/api/v1/property", params={"query": case.query, **case.params})

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_query"] == case.query
    assert payload["response_type"] == case.response_type
    assert {item["key"] for item in payload["preferences"]} == set(case.preferences)

    assert provider.last_plan is not None
    plan = provider.last_plan
    assert plan.filter_condition.landmark_context == case.landmark_context
    assert plan.filter_condition.travel_time_limit_min == case.travel_time_limit_min
    assert plan.filter_condition.search_radius_meters == case.search_radius_meters
    assert plan.semantic_extraction.get("transport_mode") == case.transport_mode

    assert repo.calls
    mongo_query = repo.calls[-1][1]
    _assert_mongo_query_matches_case(mongo_query, case)
