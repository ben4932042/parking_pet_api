import pytest

from application.property import PropertyService
from domain.entities.property import PropertyFilterCondition
from domain.entities.search import SearchPlan
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.services.property_enrichment import IEnrichmentProvider


class DummyEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, geocode_result=("landmark", None)):
        self.geocode_result = geocode_result

    def create_property_by_name(self, property_name: str):
        raise NotImplementedError

    def generate_ai_analysis(self, source):
        raise NotImplementedError

    def extract_search_plan(self, query: str) -> SearchPlan:
        raise NotImplementedError

    def geocode_landmark(self, landmark_name: str):
        return self.geocode_result


class DummyRepo(IPropertyRepository):
    def __init__(self, items):
        self.items = items

    async def find_by_query(self, query, open_at_minutes=None):
        return list(self.items)

    async def get_by_keyword(self, q):
        return []

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


class RankingEnrichmentProvider(DummyEnrichmentProvider):
    def __init__(self, condition):
        super().__init__()
        self.condition = condition

    def extract_search_plan(self, query: str) -> SearchPlan:
        return SearchPlan(route="semantic", filter_condition=self.condition)


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

    query = provider.generate_query(
        condition, user_coords=None, map_coords=(121.0, 25.0)
    )

    assert query == {"primary_type": "cafe"}


def test_property_filter_condition_defaults_to_neutral_rating_gate():
    intent = PropertyFilterCondition(mongo_query={})

    assert intent.min_rating == 0.0


@pytest.mark.asyncio
async def test_search_reranks_by_distance_when_geo_context_exists(
    property_entity_factory,
):
    far_high_rating = property_entity_factory(
        identifier="far-high-rating",
        latitude=25.05,
        longitude=121.60,
        rating=4.8,
        pet_menu=True,
        free_water=True,
    )
    near_good_rating = property_entity_factory(
        identifier="near-good-rating",
        latitude=25.031,
        longitude=121.561,
        rating=4.4,
        pet_menu=True,
        free_water=True,
    )
    service = PropertyService(
        repo=DummyRepo([far_high_rating, near_good_rating]),
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=DummyAuditRepo(),
        enrichment_provider=RankingEnrichmentProvider(
            PropertyFilterCondition(
                mongo_query={"primary_type": "cafe"},
                landmark_context="CURRENT_LOCATION",
                search_radius_meters=10000,
            )
        ),
    )

    results, _ = await service.search_by_keyword(
        q="dog cafe nearby",
        user_coords=(121.56, 25.03),
        map_coords=None,
    )

    assert [item.id for item in results] == ["near-good-rating", "far-high-rating"]


@pytest.mark.asyncio
async def test_search_reranks_by_pet_feature_density_beyond_repo_order(
    property_entity_factory,
):
    low_feature_high_rating = property_entity_factory(
        identifier="low-feature-high-rating",
        latitude=25.03,
        longitude=121.56,
        rating=4.7,
        pet_menu=False,
        free_water=False,
        allow_on_floor=False,
        spacious=False,
    )
    high_feature_lower_rating = property_entity_factory(
        identifier="high-feature-lower-rating",
        latitude=25.03,
        longitude=121.56,
        rating=4.3,
        pet_menu=True,
        free_water=True,
        allow_on_floor=True,
        spacious=True,
    )
    service = PropertyService(
        repo=DummyRepo([low_feature_high_rating, high_feature_lower_rating]),
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=DummyAuditRepo(),
        enrichment_provider=RankingEnrichmentProvider(
            PropertyFilterCondition(mongo_query={"primary_type": "cafe"})
        ),
    )

    results, _ = await service.search_by_keyword(
        q="pet cafe", user_coords=None, map_coords=None
    )

    assert [item.id for item in results] == [
        "high-feature-lower-rating",
        "low-feature-high-rating",
    ]
