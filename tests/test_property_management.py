import pytest

from application.property import PropertyService
from domain.entities.audit import ActorInfo, PropertyAuditAction
from domain.entities.enrichment import AIAnalysis, AnalysisSource, PetEnvironment, PetFeatures, PetRules, PetService
from domain.entities.property import (
    OpeningPeriod,
    PetEnvironmentOverride,
    PetFeaturesOverride,
    PetRulesOverride,
    PetServiceOverride,
    PropertyEntity,
    TimePoint,
)
from domain.services.property_enrichment import IEnrichmentProvider


def build_property(
    *,
    identifier: str,
    place_id: str,
    rating: float = 4.0,
    free_water: bool = False,
    pet_menu: bool = False,
    allow_on_floor: bool = False,
    deleted: bool = False,
):
    return PropertyEntity(
        _id=identifier,
        name="test-property",
        place_id=place_id,
        latitude=25.03,
        longitude=121.56,
        regular_opening_hours=[
            OpeningPeriod(
                open=TimePoint(day=0, hour=0, minute=0),
                close=TimePoint(day=6, hour=23, minute=59),
            )
        ],
        address="test",
        primary_type="cafe",
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
                    spacious=False,
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
        is_deleted=deleted,
    )


class InMemoryPropertyRepo:
    def __init__(self, property_entity: PropertyEntity | None = None):
        self.property_entity = property_entity

    async def get_by_keyword(self, q: str):
        return []

    async def get_nearby(self, lat, lng, radius, types, page, size):
        return [], 0

    async def get_property_by_id(self, property_id, include_deleted=False):
        if self.property_entity is None:
            return None
        if not include_deleted and self.property_entity.is_deleted:
            return None
        return self.property_entity

    async def get_property_by_place_id(self, place_id, include_deleted=False):
        if self.property_entity is None or self.property_entity.place_id != place_id:
            return None
        if not include_deleted and self.property_entity.is_deleted:
            return None
        return self.property_entity

    async def get_properties_by_ids(self, property_ids):
        return []

    async def create(self, new_property):
        self.property_entity = new_property

    async def find_by_query(self, query):
        return []

    async def save(self, property_entity):
        self.property_entity = property_entity
        return property_entity


class InMemoryAuditRepo:
    def __init__(self):
        self.logs = []

    async def create(self, audit_log):
        self.logs.append(audit_log)
        return audit_log

    async def list_by_property_id(self, property_id, limit=50):
        return [log for log in self.logs if log.property_id == property_id][:limit]


class DummyRawDataRepo:
    def __init__(self):
        self.saved = []

    async def create(self, source):
        self.saved.append(source)

    async def save(self, source):
        self.saved.append(source)


class SyncEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, source: AnalysisSource, synced_property: PropertyEntity):
        self.source = source
        self.synced_property = synced_property

    def create_property_by_name(self, property_name: str) -> AnalysisSource:
        return self.source

    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity:
        return self.synced_property

    def extract_search_criteria(self, query: str):
        raise NotImplementedError

    def geocode_landmark(self, landmark_name: str):
        return landmark_name, None


def build_source(place_id: str) -> AnalysisSource:
    return AnalysisSource(
        _id=place_id,
        id=place_id,
        origin_search_name="test",
        display_name="test",
        place_id=place_id,
        latitude=25.03,
        longitude=121.56,
        address="test",
        primary_type="cafe",
        types=["cafe"],
        user_rating_count=10,
        reviews=[],
        regular_opening_hours=[],
    )


def actor() -> ActorInfo:
    return ActorInfo(user_id="u1", name="Ben", role="user", source="user")


@pytest.mark.asyncio
async def test_update_pet_features_merges_manual_override_and_writes_audit_log():
    repo = InMemoryPropertyRepo(build_property(identifier="p1", place_id="place-1", free_water=False))
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), repo.property_entity),
    )

    detail = await service.update_pet_features(
        property_id="p1",
        pet_rules=PetRulesOverride(allow_on_floor=True),
        pet_environment=None,
        pet_service=PetServiceOverride(free_water=True),
        actor=actor(),
        reason="verified on site",
    )

    assert detail.effective_pet_features.rules.allow_on_floor is True
    assert detail.effective_pet_features.services.free_water is True
    assert detail.manual_overrides.pet_features.services.free_water is True
    assert audit_repo.logs[-1].action == PropertyAuditAction.PET_FEATURES_OVERRIDE


@pytest.mark.asyncio
async def test_sync_preserves_manual_override_and_writes_sync_audit():
    existing = build_property(identifier="p1", place_id="place-1", free_water=False)
    existing.manual_overrides = existing.manual_overrides or None
    existing = PropertyEntity(
        **existing.model_dump(
            by_alias=True,
            exclude_none=True,
        ),
        manual_overrides={
            "pet_features": {
                "services": {"free_water": True},
            }
        },
    )
    synced = build_property(identifier="place-1", place_id="place-1", free_water=False, pet_menu=True)
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), synced),
    )

    saved = await service.create_property(name="test", actor=actor())

    assert saved.effective_pet_features.services.free_water is True
    assert saved.ai_analysis.pet_features.services.pet_menu is True
    assert audit_repo.logs[-1].action == PropertyAuditAction.SYNC


@pytest.mark.asyncio
async def test_soft_delete_and_restore_write_audit_logs():
    repo = InMemoryPropertyRepo(build_property(identifier="p1", place_id="place-1"))
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), repo.property_entity),
    )

    deleted = await service.soft_delete_property("p1", actor=actor(), reason="duplicate")
    restored = await service.restore_property("p1", actor=actor(), reason="restored")

    assert deleted.is_deleted is True
    assert restored.is_deleted is False
    assert [log.action for log in audit_repo.logs[-2:]] == [
        PropertyAuditAction.SOFT_DELETE,
        PropertyAuditAction.RESTORE,
    ]


@pytest.mark.asyncio
async def test_get_audit_logs_returns_property_history():
    repo = InMemoryPropertyRepo(build_property(identifier="p1", place_id="place-1"))
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), repo.property_entity),
    )

    await service.soft_delete_property("p1", actor=actor(), reason="duplicate")
    logs = await service.get_audit_logs("p1", limit=10)

    assert len(logs) == 1
    assert logs[0].actor.user_id == "u1"
