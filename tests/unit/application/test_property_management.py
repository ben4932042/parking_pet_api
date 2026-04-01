import pytest

from application.property import PropertyService
from application.exceptions import ConflictError, NotFoundError
from domain.entities.audit import PropertyAuditAction
from domain.entities.enrichment import AnalysisSource
from domain.entities.property import (
    PetRulesOverride,
    PetFeaturesOverride,
    PetServiceOverride,
    PropertyEntity,
    PropertyManualOverrides,
)
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.services.property_enrichment import IEnrichmentProvider
from domain.entities.search import SearchPlan


class InMemoryPropertyRepo(IPropertyRepository):
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


class InMemoryAuditRepo(IPropertyAuditRepository):
    def __init__(self):
        self.logs = []

    async def create(self, audit_log):
        self.logs.append(audit_log)
        return audit_log

    async def list_by_property_id(self, property_id, limit=50):
        return [log for log in self.logs if log.property_id == property_id][:limit]


class DummyRawDataRepo(IPlaceRawDataRepository):
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

    def extract_search_plan(self, query: str) -> SearchPlan:
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


@pytest.mark.asyncio
async def test_update_pet_features_merges_manual_override_and_writes_audit_log(
    property_entity_factory, actor_factory
):
    repo = InMemoryPropertyRepo(
        property_entity_factory(identifier="p1", place_id="place-1", free_water=False)
    )
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(
            build_source("place-1"), repo.property_entity
        ),
    )

    detail = await service.update_pet_features(
        property_id="p1",
        pet_rules=PetRulesOverride(allow_on_floor=True),
        pet_environment=None,
        pet_service=PetServiceOverride(free_water=True),
        actor=actor_factory(),
        reason="verified on site",
    )

    assert detail.effective_pet_features.rules.allow_on_floor is True
    assert detail.effective_pet_features.services.free_water is True
    assert detail.manual_overrides.pet_features.services.free_water is True
    assert audit_repo.logs[-1].action == PropertyAuditAction.PET_FEATURES_OVERRIDE


@pytest.mark.asyncio
async def test_sync_preserves_manual_override_and_writes_sync_audit(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(
        identifier="p1", place_id="place-1", free_water=False
    )

    manual_overrides = PropertyManualOverrides(
        pet_features=PetFeaturesOverride(services=PetServiceOverride(free_water=True))
    )
    existing = PropertyEntity(
        **existing.model_dump(
            by_alias=True,
            exclude_none=True,
        ),
        manual_overrides=manual_overrides,
    )
    synced = property_entity_factory(
        identifier="place-1", place_id="place-1", free_water=False, pet_menu=True
    )
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), synced),
    )

    saved = await service.create_property(name="test", actor=actor_factory())

    assert saved.effective_pet_features.services.free_water is True
    assert saved.ai_analysis.pet_features.services.pet_menu is True
    assert audit_repo.logs[-1].action == PropertyAuditAction.SYNC


@pytest.mark.asyncio
async def test_create_property_rejects_unknown_primary_type_for_new_record(
    property_entity_factory, actor_factory
):
    synced = property_entity_factory(
        identifier="place-unknown",
        place_id="place-unknown",
    )
    synced = synced.model_copy(update={"primary_type": "unknown"})

    repo = InMemoryPropertyRepo()
    audit_repo = InMemoryAuditRepo()
    raw_data_repo = DummyRawDataRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-unknown"), synced),
    )

    with pytest.raises(ValueError, match="unknown primary_type"):
        await service.create_property(name="test", actor=actor_factory())

    assert repo.property_entity is None
    assert audit_repo.logs == []
    assert len(raw_data_repo.saved) == 1


@pytest.mark.asyncio
async def test_soft_delete_and_restore_write_audit_logs(
    property_entity_factory, actor_factory
):
    repo = InMemoryPropertyRepo(
        property_entity_factory(identifier="p1", place_id="place-1")
    )
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(
            build_source("place-1"), repo.property_entity
        ),
    )

    deleted = await service.soft_delete_property(
        "p1", actor=actor_factory(), reason="duplicate"
    )
    restored = await service.restore_property(
        "p1", actor=actor_factory(), reason="restored"
    )

    assert deleted.is_deleted is True
    assert restored.is_deleted is False
    assert [log.action for log in audit_repo.logs[-2:]] == [
        PropertyAuditAction.SOFT_DELETE,
        PropertyAuditAction.RESTORE,
    ]


@pytest.mark.asyncio
async def test_get_audit_logs_returns_property_history(
    property_entity_factory, actor_factory
):
    repo = InMemoryPropertyRepo(
        property_entity_factory(identifier="p1", place_id="place-1")
    )
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(
            build_source("place-1"), repo.property_entity
        ),
    )

    await service.soft_delete_property("p1", actor=actor_factory(), reason="duplicate")
    logs = await service.get_audit_logs("p1", limit=10)

    assert len(logs) == 1
    assert logs[0].actor.user_id == "u1"


@pytest.mark.asyncio
async def test_create_property_new_record_writes_create_audit_and_actor(
    property_entity_factory, actor_factory
):
    created = property_entity_factory(identifier="place-1", place_id="place-1")
    repo = InMemoryPropertyRepo(None)
    audit_repo = InMemoryAuditRepo()
    raw_repo = DummyRawDataRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_repo,
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), created),
    )

    saved = await service.create_property(name="test", actor=actor_factory())

    assert saved.id == "place-1"
    assert saved.created_by.user_id == "u1"
    assert len(raw_repo.saved) == 1
    assert audit_repo.logs[-1].action == PropertyAuditAction.CREATE


@pytest.mark.asyncio
async def test_create_property_rejects_soft_deleted_existing_record(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(
        identifier="p1", place_id="place-1", deleted=True
    )
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=audit_repo,
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), existing),
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.create_property(name="test", actor=actor_factory())

    assert "soft-deleted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_pet_features_requires_at_least_one_override(
    property_entity_factory, actor_factory
):
    repo = InMemoryPropertyRepo(
        property_entity_factory(identifier="p1", place_id="place-1")
    )
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=InMemoryAuditRepo(),
        enrichment_provider=SyncEnrichmentProvider(
            build_source("place-1"), repo.property_entity
        ),
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.update_pet_features(
            property_id="p1",
            pet_rules=None,
            pet_environment=None,
            pet_service=None,
            actor=actor_factory(),
            reason=None,
        )

    assert "At least one pet feature override" in str(exc_info.value)


@pytest.mark.asyncio
async def test_restore_property_rejects_when_property_is_not_deleted(
    property_entity_factory, actor_factory
):
    repo = InMemoryPropertyRepo(
        property_entity_factory(identifier="p1", place_id="place-1", deleted=False)
    )
    service = PropertyService(
        repo=repo,
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=InMemoryAuditRepo(),
        enrichment_provider=SyncEnrichmentProvider(
            build_source("place-1"), repo.property_entity
        ),
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.restore_property("p1", actor=actor_factory(), reason=None)

    assert "not deleted" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_audit_logs_raises_not_found_for_missing_property(actor_factory):
    service = PropertyService(
        repo=InMemoryPropertyRepo(None),
        raw_data_repo=DummyRawDataRepo(),
        audit_repo=InMemoryAuditRepo(),
        enrichment_provider=SyncEnrichmentProvider(build_source("place-1"), None),
    )

    with pytest.raises(NotFoundError):
        await service.get_audit_logs("missing", limit=10)
