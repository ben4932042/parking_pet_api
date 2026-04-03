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

    def renew_property_from_details(self, source):
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

    async def get_by_place_id(self, place_id: str):
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


def test_generate_query_does_not_apply_map_geo_for_address_queries():
    provider = DummyEnrichmentProvider()
    condition = PropertyFilterCondition(
        mongo_query={
            "address": {"$regex": "台北", "$options": "i"},
            "primary_type": {"$in": ["restaurant", "bistro"]},
        },
        search_radius_meters=10000,
    )

    query = provider.generate_query(
        condition,
        user_coords=(121.221859793306, 25.011705336264292),
        map_coords=(121.221859793306, 25.011705336264292),
    )

    assert query == {
        "address": {"$regex": "台北", "$options": "i"},
        "primary_type": {"$in": ["restaurant", "bistro"]},
    }


def test_generate_query_uses_map_geo_for_browse_queries_without_address_or_landmark():
    provider = DummyEnrichmentProvider()
    condition = PropertyFilterCondition(
        mongo_query={"primary_type": "park"},
        search_radius_meters=2500,
    )

    query = provider.generate_query(
        condition,
        user_coords=(121.221859793306, 25.011705336264292),
        map_coords=(121.25874722747007, 24.951597027520226),
    )

    assert query == {
        "primary_type": "park",
        "location": {
            "$nearSphere": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [121.25874722747007, 24.951597027520226],
                },
                "$maxDistance": 2500,
            }
        },
    }


def test_generate_query_uses_current_location_for_current_location_landmark_context():
    provider = DummyEnrichmentProvider()
    condition = PropertyFilterCondition(
        mongo_query={"primary_type": "cafe"},
        landmark_context="CURRENT_LOCATION",
        search_radius_meters=3000,
    )

    query = provider.generate_query(
        condition,
        user_coords=(121.5645, 25.0339),
        map_coords=(121.221859793306, 25.011705336264292),
    )

    assert query == {
        "primary_type": "cafe",
        "location": {
            "$nearSphere": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [121.5645, 25.0339],
                },
                "$maxDistance": 3000,
            }
        },
    }


def test_generate_query_uses_geocoded_landmark_instead_of_map_coords():
    provider = DummyEnrichmentProvider(geocode_result=("台北101", (121.5645, 25.0339)))
    condition = PropertyFilterCondition(
        mongo_query={"primary_type": "cafe"},
        landmark_context="台北101",
        search_radius_meters=5000,
    )

    query = provider.generate_query(
        condition,
        user_coords=(121.221859793306, 25.011705336264292),
        map_coords=(121.221859793306, 25.011705336264292),
    )

    assert query == {
        "primary_type": "cafe",
        "location": {
            "$nearSphere": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": [121.5645, 25.0339],
                },
                "$maxDistance": 5000,
            }
        },
    }


def test_property_filter_condition_defaults_to_neutral_rating_gate():
    intent = PropertyFilterCondition(mongo_query={})

    assert intent.min_rating == 0.0


def test_apply_radius_override_uses_client_radius_without_explicit_distance():
    plan = SearchPlan(
        route="semantic",
        filter_condition=PropertyFilterCondition(
            mongo_query={"primary_type": "park"},
            search_radius_meters=10000,
        ),
        semantic_extraction={"category": "park", "search_radius_meters": 10000},
    )

    PropertyService._apply_radius_override(plan, 2500)

    assert plan.filter_condition.search_radius_meters == 2500
    assert plan.semantic_extraction["search_radius_meters"] == 2500


def test_apply_radius_override_skips_client_radius_for_explicit_travel_time():
    plan = SearchPlan(
        route="semantic",
        filter_condition=PropertyFilterCondition(
            mongo_query={"primary_type": "park"},
            travel_time_limit_min=15,
            search_radius_meters=1125,
        ),
        semantic_extraction={"category": "park", "search_radius_meters": 1125},
    )

    PropertyService._apply_radius_override(plan, 2500)

    assert plan.filter_condition.search_radius_meters == 1125
    assert plan.semantic_extraction["search_radius_meters"] == 1125


def test_apply_radius_override_skips_client_radius_for_landmark_or_address_queries():
    landmark_plan = SearchPlan(
        route="semantic",
        filter_condition=PropertyFilterCondition(
            mongo_query={"primary_type": "cafe"},
            landmark_context="青埔",
            search_radius_meters=10000,
        ),
        semantic_extraction={"landmark": "青埔", "search_radius_meters": 10000},
    )
    address_plan = SearchPlan(
        route="semantic",
        filter_condition=PropertyFilterCondition(
            mongo_query={"address": {"$regex": "台北", "$options": "i"}},
            search_radius_meters=10000,
        ),
        semantic_extraction={"address": "台北", "search_radius_meters": 10000},
    )

    PropertyService._apply_radius_override(landmark_plan, 2500)
    PropertyService._apply_radius_override(address_plan, 2500)

    assert landmark_plan.filter_condition.search_radius_meters == 10000
    assert address_plan.filter_condition.search_radius_meters == 10000


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
