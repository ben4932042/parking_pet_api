from datetime import datetime, timezone

import pytest

from application.property import PropertyService
from domain.entities.property_note import PropertyNoteEntity
from domain.entities.search import PropertyFilterCondition, SearchPlan
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.services.property_enrichment import IEnrichmentProvider


class BoundaryRepo(IPropertyRepository):
    def __init__(self, items=None):
        self.items = items or []

    async def get_by_keyword(self, q: str):
        return list(self.items)

    async def get_nearby(self, lat, lng, radius, types, page, size):
        return list(self.items), len(self.items)

    async def get_property_by_id(self, property_id, include_deleted=False):
        for item in self.items:
            if item.id == property_id:
                return item
        return None

    async def get_property_by_place_id(self, place_id, include_deleted=False):
        raise NotImplementedError

    async def get_properties_by_ids(self, property_ids):
        order = {property_id: index for index, property_id in enumerate(property_ids)}
        filtered = [item for item in self.items if item.id in order]
        return sorted(filtered, key=lambda item: order[item.id])

    async def create(self, new_property):
        raise NotImplementedError

    async def find_by_query(self, query, open_at_minutes=None):
        return list(self.items)

    async def save(self, property_entity):
        raise NotImplementedError


class BoundaryRawRepo(IPlaceRawDataRepository):
    async def create(self, source):
        raise NotImplementedError

    async def save(self, source):
        raise NotImplementedError

    async def get_by_place_id(self, place_id: str):
        raise NotImplementedError


class BoundaryAuditRepo(IPropertyAuditRepository):
    async def create(self, audit_log):
        return audit_log

    async def list_by_property_id(self, property_id, limit=50):
        return []


class BoundaryEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, plan: SearchPlan):
        self.plan = plan

    def create_property_by_name(self, property_name: str):
        raise NotImplementedError

    def renew_property_from_details(self, source):
        raise NotImplementedError

    def generate_ai_analysis(self, source):
        raise NotImplementedError

    def extract_search_plan(self, query: str) -> SearchPlan:
        return self.plan

    def geocode_landmark(self, landmark_name: str):
        return landmark_name, None


@pytest.mark.asyncio
async def test_search_properties_returns_personalized_dto(
    property_entity_factory, user_entity_factory
):
    items = [
        property_entity_factory(identifier="p1", name="Cafe 1", primary_type="cafe"),
        property_entity_factory(
            identifier="p2",
            name="Restaurant 1",
            primary_type="restaurant",
        ),
    ]
    service = PropertyService(
        repo=BoundaryRepo(items),
        raw_data_repo=BoundaryRawRepo(),
        audit_repo=BoundaryAuditRepo(),
        enrichment_provider=BoundaryEnrichmentProvider(
            SearchPlan(
                execution_modes=["semantic", "keyword"],
                filter_condition=PropertyFilterCondition(
                    preferences=[{"key": "pet_menu_preference", "label": "pet_menu=True"}]
                ),
            )
        ),
    )
    current_user = user_entity_factory(
        identifier="u1",
        favorite_property_ids=["p1"],
        property_notes=[
            PropertyNoteEntity(
                property_id="p2",
                content="saved",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
    )

    result = await service.search_properties("台北", current_user=current_user)

    assert result.response_type == "hybrid_search"
    assert result.categories == ["cafe", "restaurant"]
    assert result.preferences == [
        {"key": "pet_menu_preference", "label": "pet_menu=True"}
    ]
    assert result.results[0].is_favorite is True
    assert result.results[0].has_note is False
    assert result.results[1].has_note is True


@pytest.mark.asyncio
async def test_get_overviews_by_ids_can_sort_noted_items_first(
    property_entity_factory, user_entity_factory
):
    items = [
        property_entity_factory(identifier="p2", name="Cafe 2"),
        property_entity_factory(identifier="p1", name="Cafe 1"),
    ]
    service = PropertyService(
        repo=BoundaryRepo(items),
        raw_data_repo=BoundaryRawRepo(),
        audit_repo=BoundaryAuditRepo(),
        enrichment_provider=BoundaryEnrichmentProvider(
            SearchPlan(execution_modes=["keyword"])
        ),
    )
    current_user = user_entity_factory(
        identifier="u1",
        favorite_property_ids=["p1", "p2"],
        property_notes=[
            PropertyNoteEntity(
                property_id="p1",
                content="saved",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
    )

    results = await service.get_overviews_by_ids(
        ["p2", "p1"],
        current_user=current_user,
        note_first=True,
    )

    assert [item.id for item in results] == ["p1", "p2"]
    assert [item.has_note for item in results] == [True, False]


@pytest.mark.asyncio
async def test_get_details_returns_property_detail_dto(property_entity_factory):
    item = property_entity_factory(identifier="p1", free_water=True, pet_menu=True)
    service = PropertyService(
        repo=BoundaryRepo([item]),
        raw_data_repo=BoundaryRawRepo(),
        audit_repo=BoundaryAuditRepo(),
        enrichment_provider=BoundaryEnrichmentProvider(
            SearchPlan(execution_modes=["keyword"])
        ),
    )

    detail = await service.get_details("p1")

    assert detail is not None
    assert detail.id == "p1"
    assert detail.ai_analysis.rating == item.ai_analysis.ai_rating
    assert detail.effective_pet_features.services.free_water is True
