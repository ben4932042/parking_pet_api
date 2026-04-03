import pytest

from application.property import PropertyService
from application.exceptions import ConflictError, NotFoundError
from domain.entities.audit import PropertyAuditAction
from domain.entities.enrichment import AnalysisSource, Review
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
    def __init__(self, existing: AnalysisSource | None = None):
        self.existing = existing
        self.saved = []

    async def create(self, source):
        self.saved.append(source)

    async def save(self, source):
        self.existing = source
        self.saved.append(source)

    async def get_by_place_id(self, place_id: str) -> AnalysisSource | None:
        if self.existing is None or self.existing.place_id != place_id:
            return None
        return self.existing


class SyncEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, source: AnalysisSource, synced_property: PropertyEntity):
        self.source = source
        self.synced_property = synced_property
        self.generate_calls: list[AnalysisSource] = []
        self.details_calls: list[AnalysisSource] = []

    def create_property_by_name(self, property_name: str) -> AnalysisSource:
        return self.source

    def renew_property_from_details(self, source: AnalysisSource) -> AnalysisSource:
        self.details_calls.append(source)
        return self.source

    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity:
        self.generate_calls.append(source)
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


def build_review(author: str | None, rating: float, text: str) -> Review:
    return Review(author=author, rating=rating, text=text, time="today")


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
    old_source = build_source("place-1").model_copy(
        update={"reviews": [build_review("alice", 5, "old text")]}
    )
    latest_source = build_source("place-1").model_copy(
        update={"reviews": [build_review("alice", 5, "new text")]}
    )
    raw_data_repo = DummyRawDataRepo(existing=old_source)
    provider = SyncEnrichmentProvider(latest_source, synced)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=provider,
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
        enrichment_provider=SyncEnrichmentProvider(
            build_source("place-unknown"), synced
        ),
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
async def test_sync_skips_llm_when_user_rating_count_and_reviews_are_unchanged(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1")
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    existing_source = build_source("place-1").model_copy(
        update={"user_rating_count": 10, "reviews": [build_review("alice", 5, "same")]}
    )
    raw_data_repo = DummyRawDataRepo(existing=existing_source)
    provider = SyncEnrichmentProvider(existing_source, existing.model_copy())
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=provider,
    )

    saved = await service.create_property(name="test", actor=actor_factory())

    assert saved == existing
    assert provider.generate_calls == []
    assert audit_repo.logs == []
    assert raw_data_repo.saved[-1].reviews == [build_review("alice", 5, "same")]


@pytest.mark.asyncio
async def test_sync_reruns_llm_when_user_rating_count_changes(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1")
    synced = property_entity_factory(identifier="place-1", place_id="place-1")
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    old_source = build_source("place-1").model_copy(
        update={"user_rating_count": 10, "reviews": [build_review("alice", 5, "same")]}
    )
    latest_source = build_source("place-1").model_copy(
        update={"user_rating_count": 11, "reviews": [build_review("alice", 5, "same")]}
    )
    raw_data_repo = DummyRawDataRepo(existing=old_source)
    provider = SyncEnrichmentProvider(latest_source, synced)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=provider,
    )

    saved = await service.create_property(name="test", actor=actor_factory())

    assert saved.id == existing.id
    assert provider.generate_calls == [raw_data_repo.saved[-1]]
    assert raw_data_repo.saved[-1].user_rating_count == 11
    assert audit_repo.logs[-1].action == PropertyAuditAction.SYNC


@pytest.mark.asyncio
async def test_sync_reruns_llm_when_review_content_changes_for_same_author(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1")
    synced = property_entity_factory(identifier="place-1", place_id="place-1")
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    old_source = build_source("place-1").model_copy(
        update={"reviews": [build_review("alice", 5, "old text")]}
    )
    latest_source = build_source("place-1").model_copy(
        update={"reviews": [build_review("alice", 5, "new text")]}
    )
    raw_data_repo = DummyRawDataRepo(existing=old_source)
    provider = SyncEnrichmentProvider(latest_source, synced)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=provider,
    )

    saved = await service.create_property(name="test", actor=actor_factory())

    assert saved.id == existing.id
    assert provider.generate_calls == [raw_data_repo.saved[-1]]
    assert raw_data_repo.saved[-1].reviews == [build_review("alice", 5, "new text")]
    assert audit_repo.logs[-1].action == PropertyAuditAction.SYNC


@pytest.mark.asyncio
async def test_sync_merges_new_reviews_and_ignores_missing_authors(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1")
    synced = property_entity_factory(identifier="place-1", place_id="place-1")
    repo = InMemoryPropertyRepo(existing)
    old_source = build_source("place-1").model_copy(
        update={"reviews": [build_review("alice", 5, "old alice")]}
    )
    latest_source = build_source("place-1").model_copy(
        update={
            "reviews": [
                build_review("bob", 4, "new bob"),
                build_review(None, 3, "anonymous"),
            ],
            "address": "new address",
            "business_status": "CLOSED_TEMPORARILY",
        }
    )
    raw_data_repo = DummyRawDataRepo(existing=old_source)
    provider = SyncEnrichmentProvider(latest_source, synced)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=InMemoryAuditRepo(),
        enrichment_provider=provider,
    )

    await service.create_property(name="test", actor=actor_factory())

    assert raw_data_repo.saved[-1].reviews == [
        build_review("alice", 5, "old alice"),
        build_review("bob", 4, "new bob"),
    ]
    assert raw_data_repo.saved[-1].address == "new address"
    assert raw_data_repo.saved[-1].business_status == "CLOSED_TEMPORARILY"
    assert provider.generate_calls == [raw_data_repo.saved[-1]]


@pytest.mark.asyncio
async def test_renew_property_in_details_mode_uses_existing_raw_source(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1")
    synced = property_entity_factory(identifier="place-1", place_id="place-1")
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    previous_source = build_source("place-1").model_copy(
        update={"user_rating_count": 10, "reviews": [build_review("alice", 5, "old")]}
    )
    renewed_source = build_source("place-1").model_copy(
        update={"user_rating_count": 11, "reviews": [build_review("alice", 5, "new")]}
    )
    raw_data_repo = DummyRawDataRepo(existing=previous_source)
    provider = SyncEnrichmentProvider(renewed_source, synced)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=provider,
    )

    saved, changed = await service.renew_property(
        property_id="p1",
        mode="details",
        actor=actor_factory(),
        reason="refresh details",
    )

    assert changed is True
    assert saved.id == existing.id
    assert provider.details_calls == [previous_source]
    assert provider.generate_calls == [raw_data_repo.saved[-1]]
    assert audit_repo.logs[-1].reason == "refresh details"


@pytest.mark.asyncio
async def test_renew_property_in_basic_mode_rejects_place_id_mismatch(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1", name="old")
    repo = InMemoryPropertyRepo(existing)
    raw_data_repo = DummyRawDataRepo(
        existing=build_source("place-1").model_copy(update={"origin_search_name": "old"})
    )
    mismatched_source = build_source("place-2")
    provider = SyncEnrichmentProvider(mismatched_source, existing)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=InMemoryAuditRepo(),
        enrichment_provider=provider,
    )

    with pytest.raises(ConflictError, match="different place_id"):
        await service.renew_property(
            property_id="p1",
            mode="basic",
            actor=actor_factory(),
        )


@pytest.mark.asyncio
async def test_renew_property_returns_unchanged_when_reviews_and_rating_count_match(
    property_entity_factory, actor_factory
):
    existing = property_entity_factory(identifier="p1", place_id="place-1")
    repo = InMemoryPropertyRepo(existing)
    audit_repo = InMemoryAuditRepo()
    previous_source = build_source("place-1").model_copy(
        update={"user_rating_count": 10, "reviews": [build_review("alice", 5, "same")]}
    )
    renewed_source = build_source("place-1").model_copy(
        update={"user_rating_count": 10, "reviews": [build_review("alice", 5, "same")]}
    )
    raw_data_repo = DummyRawDataRepo(existing=previous_source)
    provider = SyncEnrichmentProvider(renewed_source, existing)
    service = PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        enrichment_provider=provider,
    )

    saved, changed = await service.renew_property(
        property_id="p1",
        mode="details",
        actor=actor_factory(),
    )

    assert changed is False
    assert saved == existing
    assert provider.generate_calls == []
    assert audit_repo.logs == []


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


@pytest.mark.asyncio
async def test_update_aliases_merges_manual_aliases_and_writes_audit_log(
    property_entity_factory, actor_factory
):
    repo = InMemoryPropertyRepo(
        property_entity_factory(
            identifier="p1", place_id="place-1", name="青埔公七公園"
        )
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

    detail = await service.update_aliases(
        property_id="p1",
        manual_aliases=["青埔七號公園", "公七公園"],
        actor=actor_factory(),
        reason="search tuning",
    )

    assert detail.aliases == ["公七公園", "青埔七號公園"]
    assert detail.manual_aliases == ["青埔七號公園", "公七公園"]
    assert audit_repo.logs[-1].action == PropertyAuditAction.ALIASES_UPDATE
