import pytest

from domain.entities.property import PropertyFilterCondition
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.google.extract_query import SearchIntent
from interface.api.routes.v1.property import get_detail, search_properties_by_keyword


class DummyEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, geocode_result=("landmark", None)):
        self.geocode_result = geocode_result

    def create_property_by_name(self, property_name: str):
        raise NotImplementedError

    def generate_ai_analysis(self, source):
        raise NotImplementedError

    def extract_search_criteria(self, query: str):
        raise NotImplementedError

    def geocode_landmark(self, landmark_name: str):
        return self.geocode_result


class CaptureService:
    def __init__(self):
        self.calls = []

    async def search_by_keyword(self, q, user_coords=None, map_coords=None):
        self.calls.append(
            {
                "q": q,
                "user_coords": user_coords,
                "map_coords": map_coords,
            }
        )
        conditions = PropertyFilterCondition(preferences=[])
        return [], conditions


class MissingDetailService:
    async def get_details(self, property_id):
        return None


@pytest.mark.asyncio
async def test_search_route_omits_invalid_coordinate_tuples():
    service = CaptureService()

    await search_properties_by_keyword(
        query="dog cafe",
        user_lat=None,
        user_lng=None,
        map_lat=25.03,
        map_lng=121.56,
        service=service,
    )

    assert service.calls == [
        {
            "q": "dog cafe",
            "user_coords": None,
            "map_coords": (121.56, 25.03),
        }
    ]


def test_generate_query_skips_current_location_when_user_coords_missing():
    provider = DummyEnrichmentProvider()
    condition = PropertyFilterCondition(
        mongo_query={"primary_type": "cafe"},
        landmark_context="CURRENT_LOCATION",
        search_radius_meters=2000,
    )

    query = provider.generate_query(condition, user_coords=None, map_coords=None)

    assert query == {"primary_type": "cafe"}


def test_generate_query_skips_location_when_landmark_geocode_fails():
    provider = DummyEnrichmentProvider(geocode_result=("taipei 101", None))
    condition = PropertyFilterCondition(
        mongo_query={"primary_type": "cafe"},
        landmark_context="taipei 101",
        search_radius_meters=2000,
    )

    query = provider.generate_query(condition, user_coords=None, map_coords=(121.0, 25.0))

    assert query == {"primary_type": "cafe"}


def test_search_intent_defaults_to_neutral_rating_gate():
    intent = SearchIntent(
        mongo_query={},
        matched_fields=[],
        preferences=[],
        explanation="neutral search",
    )

    assert intent.min_rating == 0.0


@pytest.mark.asyncio
async def test_get_detail_returns_404_when_service_has_no_property():
    service = MissingDetailService()

    with pytest.raises(Exception) as exc_info:
        await get_detail(property_id="missing-id", service=service)

    assert exc_info.value.status_code == 404
