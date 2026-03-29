import pytest

from application.property import PropertyService
from domain.entities.enrichment import AIAnalysis, PetEnvironment, PetFeatures, PetRules, PetService
from domain.entities.property_category import PropertyCategoryKey
from domain.entities.property import OpeningPeriod, PropertyEntity, PropertyFilterCondition, TimePoint
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.google.extract_query import SearchIntent
from interface.api.routes.v1.property import create_property, get_detail, get_nearby_properties, search_properties_by_keyword
from interface.api.exceptions.error import ConflictError
from interface.api.schemas.property import PropertyNearbyRequest


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

    async def search_nearby(self, lat, lng, radius, types, page, size):
        self.calls.append(
            {
                "lat": lat,
                "lng": lng,
                "radius": radius,
                "types": types,
                "page": page,
                "size": size,
            }
        )
        return [], 0


class MissingDetailService:
    async def get_details(self, property_id):
        return None


class CreatePropertyService:
    def __init__(self, created_property=None, error: Exception | None = None):
        self.created_property = created_property
        self.error = error

    async def create_property(self, name, actor=None):
        if self.error:
            raise self.error
        return self.created_property


class DummyRepo:
    def __init__(self, items):
        self.items = items

    async def find_by_query(self, query):
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

    def extract_search_criteria(self, query: str):
        return self.condition


class DummyRawDataRepo:
    async def create(self, source):
        raise NotImplementedError

    async def save(self, source):
        raise NotImplementedError


class DummyAuditRepo:
    async def create(self, audit_log):
        return audit_log

    async def list_by_property_id(self, property_id, limit=50):
        return []


def build_property(
    *,
    identifier: str,
    latitude: float,
    longitude: float,
    rating: float,
    primary_type: str = "cafe",
    is_open: bool = True,
    pet_menu: bool = False,
    free_water: bool = False,
    allow_on_floor: bool = False,
    spacious: bool = False,
):
    entity = PropertyEntity(
        _id=identifier,
        name=identifier,
        place_id=identifier,
        latitude=latitude,
        longitude=longitude,
        regular_opening_hours=[
            OpeningPeriod(
                open=TimePoint(day=0, hour=0, minute=0),
                close=TimePoint(day=6, hour=23, minute=59),
            )
        ],
        address="Test address",
        primary_type=primary_type,
        ai_analysis=AIAnalysis(
            venue_type="pet-friendly cafe",
            ai_summary="summary",
            pet_features=PetFeatures(
                rules=PetRules(
                    leash_required=False,
                    stroller_required=False,
                    allow_on_floor=allow_on_floor,
                ),
                environment=PetEnvironment(
                    stairs=False,
                    outdoor_seating=False,
                    spacious=spacious,
                    indoor_ac=True,
                    off_leash_possible=False,
                    pet_friendly_floor=True,
                    has_shop_pet=False,
                ),
                services=PetService(
                    pet_menu=pet_menu,
                    free_water=free_water,
                    free_treats=False,
                    pet_seating=False,
                ),
            ),
            highlights=["friendly"],
            warnings=[],
            rating=rating,
        ),
    )
    entity.is_open = is_open
    return entity


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


@pytest.mark.asyncio
async def test_nearby_route_expands_category_to_primary_types():
    service = CaptureService()

    await get_nearby_properties(
        params=PropertyNearbyRequest(
            lat=25.03,
            lng=121.56,
            radius=1000,
            category=PropertyCategoryKey.RESTAURANT,
            page=1,
            size=20,
        ),
        service=service,
    )

    assert len(service.calls) == 1
    call = service.calls[0]
    assert call["lat"] == 25.03
    assert call["lng"] == 121.56
    assert call["radius"] == 1000
    assert call["page"] == 1
    assert call["size"] == 20
    assert "restaurant" in call["types"]
    assert "brunch_restaurant" in call["types"]
    assert "bar" in call["types"]


@pytest.mark.asyncio
async def test_create_property_route_returns_property_id_on_success():
    service = CreatePropertyService(created_property=build_property(identifier="p1", latitude=25.03, longitude=121.56, rating=4.0))

    response = await create_property(name="Dessert Cafe", service=service, actor=None)

    assert response.property_id == "p1"


@pytest.mark.asyncio
async def test_create_property_route_returns_400_with_reason_on_failure():
    service = CreatePropertyService(error=ConflictError("Property is soft-deleted. Restore it before syncing again."))

    with pytest.raises(Exception) as exc_info:
        await create_property(name="Dessert Cafe", service=service, actor=None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Property is soft-deleted. Restore it before syncing again."


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


@pytest.mark.asyncio
async def test_search_reranks_by_distance_when_geo_context_exists():
    far_high_rating = build_property(
        identifier="far-high-rating",
        latitude=25.05,
        longitude=121.60,
        rating=4.8,
        pet_menu=True,
        free_water=True,
    )
    near_good_rating = build_property(
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
async def test_search_reranks_by_pet_feature_density_beyond_repo_order():
    low_feature_high_rating = build_property(
        identifier="low-feature-high-rating",
        latitude=25.03,
        longitude=121.56,
        rating=4.7,
        pet_menu=False,
        free_water=False,
        allow_on_floor=False,
        spacious=False,
    )
    high_feature_lower_rating = build_property(
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

    results, _ = await service.search_by_keyword(q="pet cafe", user_coords=None, map_coords=None)

    assert [item.id for item in results] == ["high-feature-lower-rating", "low-feature-high-rating"]
