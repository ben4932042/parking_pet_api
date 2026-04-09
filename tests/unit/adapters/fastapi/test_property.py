import logging
from datetime import datetime, timezone

import pytest

from application.dto.property import ActorDto
from domain.entities.audit import PropertyAuditAction, PropertyAuditLog
from domain.entities.property_note import PropertyNoteEntity
from domain.entities.property import (
    PropertyEntity,
    PropertyManualOverrides,
    PetFeaturesOverride,
    PetServiceOverride,
)
from domain.entities.property_category import (
    PropertyCategoryKey,
    get_primary_types_by_category_key,
)
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_current_user,
    get_optional_request_actor,
    get_request_actor,
    get_user_service,
)
from interface.api.exceptions.error import ConflictError


def _overview_payload(item, *, has_note=False, is_favorite=False):
    return {
        "id": item.id,
        "name": item.name,
        "address": item.address,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "category": item.category,
        "types": item.types,
        "rating": item.rating,
        "is_open": item.is_open,
        "has_note": has_note,
        "is_favorite": is_favorite,
    }


def _actor_payload(actor):
    if actor is None:
        return None
    if isinstance(actor, dict):
        return actor
    return ActorDto(
        user_id=actor.user_id,
        name=actor.name,
        role=actor.role,
        source=actor.source,
    ).model_dump()


def _pet_features_payload(features):
    return features.model_dump() if features else None


def _pet_features_override_payload(features):
    return features.model_dump(exclude_none=True) if features else None


def _detail_payload(item):
    return {
        "id": item.id,
        "name": item.name,
        "aliases": item.aliases,
        "manual_aliases": item.manual_aliases,
        "address": item.address,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "types": item.types,
        "rating": item.ai_analysis.ai_rating,
        "tags": item.ai_analysis.highlights,
        "regular_opening_hours": item.regular_opening_hours,
        "ai_analysis": {
            "venue_type": item.ai_analysis.venue_type,
            "ai_summary": item.ai_analysis.ai_summary,
            "pet_features": item.ai_analysis.pet_features.model_dump(),
            "highlights": item.ai_analysis.highlights,
            "warnings": item.ai_analysis.warnings,
            "rating": item.ai_analysis.ai_rating,
        },
        "manual_overrides": (
            {
                "pet_features": _pet_features_override_payload(
                    item.manual_overrides.pet_features
                ),
                "updated_by": _actor_payload(item.manual_overrides.updated_by),
                "updated_at": item.manual_overrides.updated_at,
                "reason": item.manual_overrides.reason,
            }
            if item.manual_overrides
            else None
        ),
        "effective_pet_features": _pet_features_payload(item.effective_pet_features),
        "created_by": _actor_payload(item.created_by),
        "updated_by": _actor_payload(item.updated_by),
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "deleted_by": _actor_payload(item.deleted_by),
        "deleted_at": item.deleted_at,
        "is_deleted": item.is_deleted,
    }


class CapturePropertyService:
    def __init__(
        self,
        route="semantic",
        used_fallback=False,
        items=None,
        execution_modes=None,
        fallback_reason=None,
    ):
        self.calls = []
        self.route = route
        self.used_fallback = used_fallback
        self.items = items or []
        self.execution_modes = execution_modes
        self.fallback_reason = fallback_reason

    async def search_properties(
        self,
        q,
        category=None,
        user_coords=None,
        map_coords=None,
        radius=None,
        open_at_minutes=None,
        current_user=None,
    ):
        self.calls.append(
            {
                "q": q,
                "category": category,
                "user_coords": user_coords,
                "map_coords": map_coords,
                "radius": radius,
                "open_at_minutes": open_at_minutes,
            }
        )
        noted_property_ids = (
            {note.property_id for note in current_user.property_notes}
            if current_user is not None
            else set()
        )
        favorite_property_ids = (
            set(current_user.favorite_property_ids)
            if current_user is not None
            else set()
        )
        results = [
            _overview_payload(
                item,
                has_note=item.id in noted_property_ids,
                is_favorite=item.id in favorite_property_ids,
            )
            for item in self.items
        ]
        categories = []
        for item in results:
            category_name = item["category"]
            if category_name and category_name not in categories:
                categories.append(category_name)
        response_type = (
            "hybrid_search"
            if set(self.execution_modes or [self.route]) == {"semantic", "keyword"}
            else "keyword_search"
            if (self.execution_modes or [self.route]) == ["keyword"]
            or self.used_fallback
            else "semantic_search"
        )
        return {
            "status": "success",
            "user_query": q,
            "response_type": response_type,
            "preferences": [],
            "categories": categories,
            "results": results,
        }

    async def get_nearby_overviews(
        self, lat, lng, radius, types, page, size, current_user=None
    ):
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
        noted_property_ids = (
            {note.property_id for note in current_user.property_notes}
            if current_user is not None
            else set()
        )
        favorite_property_ids = (
            set(current_user.favorite_property_ids)
            if current_user is not None
            else set()
        )
        return (
            [
                _overview_payload(
                    item,
                    has_note=item.id in noted_property_ids,
                    is_favorite=item.id in favorite_property_ids,
                )
                for item in self.items
            ],
            len(self.items),
        )

    async def get_map_overviews(
        self,
        min_lat,
        max_lat,
        min_lng,
        max_lng,
        types,
        query,
        limit,
        category=None,
        current_user=None,
    ):
        self.calls.append(
            {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lng": min_lng,
                "max_lng": max_lng,
                "types": types,
                "query": query,
                "limit": limit,
                "category": category,
            }
        )
        noted_property_ids = (
            {note.property_id for note in current_user.property_notes}
            if current_user is not None
            else set()
        )
        favorite_property_ids = (
            set(current_user.favorite_property_ids)
            if current_user is not None
            else set()
        )
        items = [
            _overview_payload(
                item,
                has_note=item.id in noted_property_ids,
                is_favorite=item.id in favorite_property_ids,
            )
            for item in self.items
        ]
        return {
            "bbox": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lng": min_lng,
                "max_lng": max_lng,
            },
            "query": query,
            "category": category.value if category is not None else None,
            "items": items,
            "total_in_bbox": len(self.items),
            "returned_count": len(items),
            "truncated": False,
            "suggest_clustering": False,
        }


class MissingDetailService:
    async def get_details(self, property_id):
        return None


class DetailService:
    def __init__(self, property_entity):
        self.property_entity = property_entity

    async def get_details(self, property_id):
        return _detail_payload(self.property_entity)


class UserServiceStub:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def record_recent_search(
        self,
        *,
        user_id,
        query,
        limit=20,
    ):
        if self.error:
            raise self.error
        self.calls.append(
            {
                "user_id": user_id,
                "query": query,
                "limit": limit,
            }
        )
        return None


class CreatePropertyService:
    def __init__(self, created_property=None, error=None):
        self.created_property = created_property
        self.error = error

    async def create_property_result(self, name, actor=None):
        if self.error:
            raise self.error
        return type(
            "CreateResultEnvelope",
            (),
            {
                "property": self.created_property,
                "result": type(
                    "CreateResult",
                    (),
                    {
                        "property_id": self.created_property.id,
                        "place_id": self.created_property.place_id,
                        "outcome": "created",
                        "changed": True,
                        "existing_before": False,
                    },
                )(),
            },
        )()


class PropertyMutationService:
    def __init__(self, property_entity=None, logs=None):
        self.property_entity = property_entity
        self.logs = logs or []
        self.calls = []
        self.renew_changed = True

    async def update_pet_features(
        self, property_id, pet_rules, pet_environment, pet_service, actor, reason=None
    ):
        self.calls.append(
            {
                "fn": "update_pet_features",
                "property_id": property_id,
                "pet_rules": pet_rules,
                "pet_environment": pet_environment,
                "pet_service": pet_service,
                "actor": actor,
                "reason": reason,
            }
        )
        return {
            "property_id": self.property_entity.id,
            "inferred_pet_features": self.property_entity.ai_analysis.pet_features.model_dump(),
            "manual_pet_features": (
                _pet_features_override_payload(
                    self.property_entity.manual_overrides.pet_features
                )
                if self.property_entity.manual_overrides
                else None
            ),
            "effective_pet_features": _pet_features_payload(
                self.property_entity.effective_pet_features
            ),
            "updated_by": _actor_payload(self.property_entity.updated_by),
            "updated_at": self.property_entity.updated_at,
            "reason": (
                self.property_entity.manual_overrides.reason
                if self.property_entity.manual_overrides
                else None
            ),
        }

    async def update_aliases(self, property_id, manual_aliases, actor, reason=None):
        self.calls.append(
            {
                "fn": "update_aliases",
                "property_id": property_id,
                "manual_aliases": manual_aliases,
                "actor": actor,
                "reason": reason,
            }
        )
        return {
            "property_id": self.property_entity.id,
            "aliases": self.property_entity.aliases,
            "manual_aliases": self.property_entity.manual_aliases,
            "updated_by": _actor_payload(self.property_entity.updated_by),
            "updated_at": self.property_entity.updated_at,
            "reason": reason,
        }

    async def soft_delete_property(self, property_id, actor, reason=None):
        self.calls.append(
            {
                "fn": "soft_delete_property",
                "property_id": property_id,
                "actor": actor,
                "reason": reason,
            }
        )
        return {
            "property_id": self.property_entity.id,
            "status": "deleted",
            "is_deleted": self.property_entity.is_deleted,
            "updated_by": _actor_payload(self.property_entity.updated_by),
            "updated_at": self.property_entity.updated_at,
            "deleted_by": _actor_payload(self.property_entity.deleted_by),
            "deleted_at": self.property_entity.deleted_at,
        }

    async def restore_property(self, property_id, actor, reason=None):
        self.calls.append(
            {
                "fn": "restore_property",
                "property_id": property_id,
                "actor": actor,
                "reason": reason,
            }
        )
        return {
            "property_id": self.property_entity.id,
            "status": "restored",
            "is_deleted": self.property_entity.is_deleted,
            "updated_by": _actor_payload(self.property_entity.updated_by),
            "updated_at": self.property_entity.updated_at,
            "deleted_by": _actor_payload(self.property_entity.deleted_by),
            "deleted_at": self.property_entity.deleted_at,
        }

    async def renew_property_result_with_outcome(
        self, property_id, mode, actor, reason=None
    ):
        self.calls.append(
            {
                "fn": "renew_property",
                "property_id": property_id,
                "mode": mode,
                "actor": actor,
                "reason": reason,
            }
        )
        mutation = {
            "property_id": self.property_entity.id,
            "status": "renewed" if self.renew_changed else "unchanged",
            "is_deleted": self.property_entity.is_deleted,
            "updated_by": _actor_payload(self.property_entity.updated_by),
            "updated_at": self.property_entity.updated_at,
            "deleted_by": _actor_payload(self.property_entity.deleted_by),
            "deleted_at": self.property_entity.deleted_at,
        }
        return type(
            "MutationResult",
            (),
            {
                "mutation": mutation,
                "place_id": self.property_entity.place_id,
                "operation": "renew",
                "outcome": "renewed" if self.renew_changed else "unchanged",
                "changed": self.renew_changed,
                "existing_before": True,
                "reason": reason,
                "mode": mode,
            },
        )()

    async def get_audit_logs(self, property_id, limit=50):
        self.calls.append(
            {
                "fn": "get_audit_logs",
                "property_id": property_id,
                "limit": limit,
            }
        )
        return [
            {
                "property_id": log.property_id,
                "action": log.action.value,
                "actor": _actor_payload(log.actor),
                "reason": log.reason,
                "source": log.source,
                "changes": log.changes,
                "before": log.before,
                "after": log.after,
                "created_at": log.created_at,
            }
            for log in self.logs
        ]


@pytest.fixture
def anonymous_actor_override(actor_factory):
    return actor_factory(
        name="anonymous-api", role="anonymous", source="api", user_id=None
    )


@pytest.fixture
def request_actor_override(actor_factory):
    return actor_factory()


@pytest.fixture(autouse=True)
def search_history_service_override(override_api_dep):
    return override_api_dep(get_user_service, UserServiceStub())


def test_search_route_omits_invalid_coordinate_tuples(
    client, override_api_dep, user_entity_factory, caplog
):
    service = override_api_dep(get_property_service, CapturePropertyService())
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.get(
            "/api/v1/property",
            params={
                "query": "dog cafe",
                "map_lat": 25.03,
                "map_lng": 121.56,
            },
        )

    assert response.status_code == 200
    assert response.json()["response_type"] == "semantic_search"
    assert response.json()["user_query"] == "dog cafe"
    assert service.calls == [
        {
            "q": "dog cafe",
            "category": None,
            "user_coords": None,
            "map_coords": (121.56, 25.03),
            "radius": None,
            "open_at_minutes": None,
        }
    ]
    record = next(
        record
        for record in caplog.records
        if record.event == "property_search_executed"
    )
    assert record.keyword == "dog cafe"
    assert record.result_count == 0


def test_search_route_returns_keyword_response_type_for_keyword_retrieval(
    client, override_api_dep, user_entity_factory
):
    override_api_dep(get_property_service, CapturePropertyService(route="keyword"))
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get("/api/v1/property", params={"query": "肉球森林"})

    assert response.status_code == 200
    assert response.json()["user_query"] == "肉球森林"
    assert response.json()["response_type"] == "keyword_search"
    assert response.json()["categories"] == []


def test_search_route_returns_keyword_response_type_for_fallback_retrieval(
    client, override_api_dep, user_entity_factory
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(route="semantic", used_fallback=True),
    )
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get("/api/v1/property", params={"query": "推薦的店"})

    assert response.status_code == 200
    assert response.json()["user_query"] == "推薦的店"
    assert response.json()["response_type"] == "keyword_search"


def test_search_route_returns_hybrid_response_type_for_dual_execution(
    client, override_api_dep, user_entity_factory
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(execution_modes=["semantic", "keyword"]),
    )
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get("/api/v1/property", params={"query": "寵物公園"})

    assert response.status_code == 200
    assert response.json()["user_query"] == "寵物公園"
    assert response.json()["response_type"] == "hybrid_search"


def test_search_route_passes_radius_to_service(
    client, override_api_dep, user_entity_factory
):
    service = override_api_dep(get_property_service, CapturePropertyService())
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get(
        "/api/v1/property",
        params={
            "query": "寵物公園",
            "map_lat": 25.03,
            "map_lng": 121.56,
            "radius": 2500,
        },
    )

    assert response.status_code == 200
    assert service.calls == [
        {
            "q": "寵物公園",
            "category": None,
            "user_coords": None,
            "map_coords": (121.56, 25.03),
            "radius": 2500,
            "open_at_minutes": None,
        }
    ]


def test_nearby_route_expands_category_to_primary_types(
    client, override_api_dep, user_entity_factory, caplog
):
    service = override_api_dep(get_property_service, CapturePropertyService())
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.get(
            "/api/v1/property/nearby",
            params={
                "lat": 25.03,
                "lng": 121.56,
                "radius": 1000,
                "category": PropertyCategoryKey.RESTAURANT,
                "page": 1,
                "size": 20,
            },
        )

    assert response.status_code == 200
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
    record = next(
        record
        for record in caplog.records
        if record.event == "property_nearby_search_executed"
    )
    assert record.lat == 25.03
    assert record.lng == 121.56
    assert record.result_count == 0


def test_nearby_route_includes_note_and_favorite_flags_for_authenticated_user(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    service = override_api_dep(
        get_property_service,
        CapturePropertyService(items=[property_entity_factory(identifier="p1")]),
    )
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        favorite_property_ids=["p1"],
        property_notes=[
            PropertyNoteEntity(
                property_id="p1",
                content="hello",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
    )
    override_api_dep(get_current_user, current_user)

    response = client.get(
        "/api/v1/property/nearby",
        params={
            "lat": 25.03,
            "lng": 121.56,
            "radius": 1000,
            "page": 1,
            "size": 20,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["id"] == "p1"
    assert data["items"][0]["has_note"] is True
    assert data["items"][0]["is_favorite"] is True
    assert service.calls == [
        {
            "lat": 25.03,
            "lng": 121.56,
            "radius": 1000,
            "types": [],
            "page": 1,
            "size": 20,
        }
    ]


def test_map_route_expands_category_and_passes_bbox_query_to_service(
    client, override_api_dep, user_entity_factory, caplog
):
    service = override_api_dep(get_property_service, CapturePropertyService())
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.get(
            "/api/v1/property/map",
            params={
                "min_lat": 25.0,
                "max_lat": 25.1,
                "min_lng": 121.5,
                "max_lng": 121.6,
                "query": " 咖啡 ",
                "category": PropertyCategoryKey.RESTAURANT,
                "limit": 300,
            },
        )

    assert response.status_code == 200
    assert service.calls == [
        {
            "min_lat": 25.0,
            "max_lat": 25.1,
            "min_lng": 121.5,
            "max_lng": 121.6,
            "types": get_primary_types_by_category_key(PropertyCategoryKey.RESTAURANT),
            "query": "咖啡",
            "limit": 300,
            "category": PropertyCategoryKey.RESTAURANT,
        }
    ]
    record = next(
        record
        for record in caplog.records
        if record.event == "property_map_search_executed"
    )
    assert record.total_in_bbox == 0
    assert record.truncated is False


def test_map_route_returns_marker_payload_with_personalization(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(items=[property_entity_factory(identifier="p1")]),
    )
    current_user = user_entity_factory(
        identifier="u1",
        favorite_property_ids=["p1"],
        property_notes=[
            PropertyNoteEntity(
                property_id="p1",
                content="saved",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
    )
    override_api_dep(get_current_user, current_user)

    response = client.get(
        "/api/v1/property/map",
        params={
            "min_lat": 25.0,
            "max_lat": 25.1,
            "min_lng": 121.5,
            "max_lng": 121.6,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["returned_count"] == 1
    assert data["truncated"] is False
    assert data["suggest_clustering"] is False
    assert data["items"][0]["id"] == "p1"
    assert data["items"][0]["has_note"] is True
    assert data["items"][0]["is_favorite"] is True
    assert data["bbox"] == {
        "min_lat": 25.0,
        "max_lat": 25.1,
        "min_lng": 121.5,
        "max_lng": 121.6,
    }


def test_map_route_rejects_invalid_bbox(client, override_api_dep, user_entity_factory):
    override_api_dep(get_property_service, CapturePropertyService())
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get(
        "/api/v1/property/map",
        params={
            "min_lat": 25.1,
            "max_lat": 25.0,
            "min_lng": 121.5,
            "max_lng": 121.6,
        },
    )

    assert response.status_code == 422


def test_search_route_passes_category_without_forcing_keyword_only_response_type(
    client, override_api_dep, user_entity_factory
):
    service = override_api_dep(
        get_property_service,
        CapturePropertyService(execution_modes=["semantic", "keyword"]),
    )
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get(
        "/api/v1/property",
        params={"query": "寵物公園", "category": PropertyCategoryKey.OUTDOOR},
    )

    assert response.status_code == 200
    assert response.json()["response_type"] == "hybrid_search"
    assert service.calls == [
        {
            "q": "寵物公園",
            "category": PropertyCategoryKey.OUTDOOR,
            "user_coords": None,
            "map_coords": None,
            "radius": None,
            "open_at_minutes": None,
        }
    ]


def test_search_route_includes_has_note_for_authenticated_user(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    service = override_api_dep(
        get_property_service,
        CapturePropertyService(items=[property_entity_factory(identifier="p1")]),
    )
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        property_notes=[
            PropertyNoteEntity(
                property_id="p1",
                content="saved",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ],
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/property", params={"query": "台北"})

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["id"] == "p1"
    assert data["categories"] == ["cafe"]
    assert data["results"][0]["has_note"] is True
    assert data["results"][0]["is_favorite"] is False
    assert service.calls == [
        {
            "q": "台北",
            "category": None,
            "user_coords": None,
            "map_coords": None,
            "radius": None,
            "open_at_minutes": None,
        }
    ]


def test_search_route_returns_unique_non_null_categories_from_results(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(
            items=[
                property_entity_factory(identifier="p1", primary_type="cafe"),
                property_entity_factory(identifier="p2", primary_type="restaurant"),
                property_entity_factory(identifier="p3", primary_type="cafe"),
            ]
        ),
    )
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get("/api/v1/property", params={"query": "台北"})

    assert response.status_code == 200
    assert response.json()["categories"] == ["cafe", "restaurant"]


def test_search_route_records_history_for_authenticated_user(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(items=[property_entity_factory(identifier="p1")]),
    )
    history_service = override_api_dep(get_user_service, UserServiceStub())
    current_user = user_entity_factory(identifier="u1", name="Ben")
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/property", params={"query": "台北咖啡廳"})

    assert response.status_code == 200
    assert history_service.calls == [
        {
            "user_id": "u1",
            "query": "台北咖啡廳",
            "limit": 20,
        }
    ]


def test_search_route_requires_authentication_header(client, override_api_dep):
    override_api_dep(get_property_service, CapturePropertyService())

    response = client.get("/api/v1/property", params={"query": "台北咖啡廳"})

    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"
    assert data["detail"] == "Authentication required"


def test_create_property_route_returns_property_id_on_success(
    client,
    override_api_dep,
    property_entity_factory,
    anonymous_actor_override,
    caplog,
):
    service = override_api_dep(
        get_property_service,
        CreatePropertyService(
            created_property=property_entity_factory(identifier="p1")
        ),
    )
    override_api_dep(get_optional_request_actor, anonymous_actor_override)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.post("/api/v1/property", params={"name": "Dessert Cafe"})

    assert response.status_code == 201
    assert response.json() == {"property_id": "p1"}
    assert service.created_property.id == "p1"
    record = next(
        record
        for record in caplog.records
        if record.event == "property_mutation_result" and record.operation == "create"
    )
    assert record.outcome == "created"
    assert record.resolved_place_id == service.created_property.place_id
    assert record.changed is True
    assert record.existing_before is False


def test_create_property_route_returns_409_with_reason_on_failure(
    client,
    override_api_dep,
    anonymous_actor_override,
    caplog,
):
    override_api_dep(
        get_property_service,
        CreatePropertyService(
            error=ConflictError(
                "Property is soft-deleted. Restore it before syncing again."
            )
        ),
    )
    override_api_dep(get_optional_request_actor, anonymous_actor_override)

    with caplog.at_level(logging.WARNING, logger="interface.api.events"):
        response = client.post("/api/v1/property", params={"name": "Dessert Cafe"})

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Property is soft-deleted. Restore it before syncing again."
    )
    record = next(
        record
        for record in caplog.records
        if record.event == "property_mutation_result" and record.operation == "create"
    )
    assert record.outcome == "rejected_soft_deleted"
    assert record.reason == "Property is soft-deleted. Restore it before syncing again."


def test_get_detail_returns_404_when_service_has_no_property(
    client, override_api_dep, user_entity_factory
):
    override_api_dep(get_property_service, MissingDetailService())
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    response = client.get("/api/v1/property/missing-id")

    assert response.status_code == 404


def test_get_detail_logs_property_viewed(
    client, override_api_dep, property_entity_factory, user_entity_factory, caplog
):
    override_api_dep(
        get_property_service,
        DetailService(property_entity_factory(identifier="p1", name="Cafe 1")),
    )
    override_api_dep(get_current_user, user_entity_factory(identifier="u1"))

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.get("/api/v1/property/p1")

    assert response.status_code == 200
    record = next(
        record for record in caplog.records if record.event == "property_viewed"
    )
    assert record.user_id == "u1"
    assert record.resource == {"type": "property", "id": "p1"}


def test_update_pet_features_route_returns_effective_and_manual_features(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
):
    property_entity = property_entity_factory(
        identifier="p1", place_id="place-1", free_water=False
    )
    property_entity = PropertyEntity(
        **property_entity.model_dump(by_alias=True, exclude={"manual_overrides"}),
        manual_overrides=PropertyManualOverrides(
            pet_features=PetFeaturesOverride(
                services=PetServiceOverride(free_water=True),
            ),
            reason="verified on site",
            updated_by=request_actor_override,
            updated_at=property_entity.updated_at,
        ),
    )
    service = override_api_dep(
        get_property_service, PropertyMutationService(property_entity=property_entity)
    )
    override_api_dep(get_request_actor, request_actor_override)

    response = client.patch(
        "/api/v1/property/p1/pet-features",
        json={
            "pet_service": {"free_water": True},
            "reason": "verified on site",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["manual_pet_features"]["services"]["free_water"] is True
    assert data["effective_pet_features"]["services"]["free_water"] is True
    assert service.calls[0]["reason"] == "verified on site"


def test_soft_delete_route_returns_deleted_status(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
):
    deleted_property = property_entity_factory(
        identifier="p1", place_id="place-1"
    ).model_copy(
        update={
            "is_deleted": True,
            "deleted_by": request_actor_override,
            "updated_by": request_actor_override,
        }
    )
    service = override_api_dep(
        get_property_service, PropertyMutationService(property_entity=deleted_property)
    )
    override_api_dep(get_request_actor, request_actor_override)

    response = client.delete("/api/v1/property/p1", params={"reason": "duplicate"})

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["status"] == "deleted"
    assert data["is_deleted"] is True
    assert service.calls[0]["reason"] == "duplicate"


def test_update_aliases_route_returns_aliases(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
):
    property_entity = property_entity_factory(
        identifier="p1", place_id="place-1", name="青埔公七公園"
    ).model_copy(
        update={
            "aliases": ["公七公園", "青埔七號公園"],
            "manual_aliases": ["青埔七號公園"],
            "updated_by": request_actor_override,
        }
    )
    service = override_api_dep(
        get_property_service, PropertyMutationService(property_entity=property_entity)
    )
    override_api_dep(get_request_actor, request_actor_override)

    response = client.patch(
        "/api/v1/property/p1/aliases",
        json={
            "manual_aliases": ["青埔七號公園"],
            "reason": "search tuning",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["aliases"] == ["公七公園", "青埔七號公園"]
    assert data["manual_aliases"] == ["青埔七號公園"]
    assert service.calls[0]["fn"] == "update_aliases"
    assert service.calls[0]["reason"] == "search tuning"


def test_restore_route_returns_restored_status(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
):
    restored_property = property_entity_factory(
        identifier="p1", place_id="place-1"
    ).model_copy(
        update={
            "is_deleted": False,
            "deleted_by": None,
            "updated_by": request_actor_override,
        }
    )
    service = override_api_dep(
        get_property_service, PropertyMutationService(property_entity=restored_property)
    )
    override_api_dep(get_request_actor, request_actor_override)

    response = client.post(
        "/api/v1/property/p1/restore", params={"reason": "restore by admin"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["status"] == "restored"
    assert data["is_deleted"] is False
    assert service.calls[0]["reason"] == "restore by admin"


def test_renew_route_forwards_mode(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
    caplog,
):
    renewed_property = property_entity_factory(
        identifier="p1", place_id="place-1"
    ).model_copy(
        update={
            "updated_by": request_actor_override,
        }
    )
    service = override_api_dep(
        get_property_service, PropertyMutationService(property_entity=renewed_property)
    )
    override_api_dep(get_request_actor, request_actor_override)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.post(
            "/api/v1/property/p1/renew",
            params={"mode": "details"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["status"] == "renewed"
    assert data["is_deleted"] is False
    assert service.calls[0]["fn"] == "renew_property"
    assert service.calls[0]["mode"] == "details"
    assert service.calls[0]["reason"] is None
    record = next(
        record
        for record in caplog.records
        if record.event == "property_mutation_result" and record.operation == "renew"
    )
    assert record.outcome == "renewed"
    assert record.mode == "details"
    assert record.resolved_place_id == renewed_property.place_id


def test_renew_route_returns_unchanged_status_when_no_data_changed(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
):
    unchanged_property = property_entity_factory(
        identifier="p1", place_id="place-1"
    ).model_copy(
        update={
            "updated_by": {
                "name": "anonymous-api",
                "role": "anonymous",
                "source": "api",
            }
        }
    )
    service = PropertyMutationService(property_entity=unchanged_property)
    service.renew_changed = False
    override_api_dep(get_property_service, service)
    override_api_dep(get_request_actor, request_actor_override)

    response = client.post(
        "/api/v1/property/p1/renew",
        params={"mode": "details"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["status"] == "unchanged"
    assert data["updated_by"]["name"] == "anonymous-api"


def test_audit_logs_route_returns_history(
    client,
    override_api_dep,
    request_actor_override,
):
    logs = [
        PropertyAuditLog(
            property_id="p1",
            action=PropertyAuditAction.PET_FEATURES_OVERRIDE,
            actor=request_actor_override,
            reason="verified",
            changes={
                "manual_overrides.pet_features.services.free_water": {
                    "before": False,
                    "after": True,
                }
            },
        )
    ]
    service = override_api_dep(get_property_service, PropertyMutationService(logs=logs))
    override_api_dep(get_request_actor, request_actor_override)

    response = client.get("/api/v1/property/p1/audit-logs", params={"limit": 10})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["property_id"] == "p1"
    assert data[0]["action"] == "pet_features_override"
    assert service.calls[0]["limit"] == 10
