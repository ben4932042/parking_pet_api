import pytest

from domain.entities.audit import PropertyAuditAction, PropertyAuditLog
from domain.entities.property import (
    PropertyEntity,
    PropertyFilterCondition,
    PropertyManualOverrides,
    PetFeaturesOverride,
    PetServiceOverride,
)
from domain.entities.search import SearchPlan
from domain.entities.property_category import PropertyCategoryKey
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_optional_current_user,
    get_optional_request_actor,
    get_request_actor,
    get_user_service,
)
from interface.api.exceptions.error import ConflictError


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

    async def search_by_keyword(
        self, q, user_coords=None, map_coords=None, radius=None, open_at_minutes=None
    ):
        self.calls.append(
            {
                "q": q,
                "user_coords": user_coords,
                "map_coords": map_coords,
                "radius": radius,
                "open_at_minutes": open_at_minutes,
            }
        )
        plan = SearchPlan(
            execution_modes=self.execution_modes or [self.route],
            filter_condition=PropertyFilterCondition(preferences=[]),
            used_fallback=self.used_fallback,
            fallback_reason=self.fallback_reason,
        )
        return self.items, plan

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
        return self.items, len(self.items)

    async def get_noted_property_ids(self, user_id: str, property_ids: list[str]):
        self.calls.append(
            {
                "fn": "get_noted_property_ids",
                "user_id": user_id,
                "property_ids": property_ids,
            }
        )
        return {"p1"}


class MissingDetailService:
    async def get_details(self, property_id):
        return None


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

    async def create_property(self, name, actor=None):
        if self.error:
            raise self.error
        return self.created_property


class PropertyMutationService:
    def __init__(self, property_entity=None, logs=None):
        self.property_entity = property_entity
        self.logs = logs or []
        self.calls = []

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
        return self.property_entity

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
        return self.property_entity

    async def soft_delete_property(self, property_id, actor, reason=None):
        self.calls.append(
            {
                "fn": "soft_delete_property",
                "property_id": property_id,
                "actor": actor,
                "reason": reason,
            }
        )
        return self.property_entity

    async def restore_property(self, property_id, actor, reason=None):
        self.calls.append(
            {
                "fn": "restore_property",
                "property_id": property_id,
                "actor": actor,
                "reason": reason,
            }
        )
        return self.property_entity

    async def get_audit_logs(self, property_id, limit=50):
        self.calls.append(
            {
                "fn": "get_audit_logs",
                "property_id": property_id,
                "limit": limit,
            }
        )
        return self.logs


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


def test_search_route_omits_invalid_coordinate_tuples(client, override_api_dep):
    service = override_api_dep(get_property_service, CapturePropertyService())

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
            "user_coords": None,
            "map_coords": (121.56, 25.03),
            "radius": None,
            "open_at_minutes": None,
        }
    ]


def test_search_route_returns_keyword_response_type_for_keyword_retrieval(
    client, override_api_dep
):
    override_api_dep(get_property_service, CapturePropertyService(route="keyword"))

    response = client.get("/api/v1/property", params={"query": "肉球森林"})

    assert response.status_code == 200
    assert response.json()["user_query"] == "肉球森林"
    assert response.json()["response_type"] == "keyword_search"


def test_search_route_returns_keyword_response_type_for_fallback_retrieval(
    client, override_api_dep
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(route="semantic", used_fallback=True),
    )

    response = client.get("/api/v1/property", params={"query": "推薦的店"})

    assert response.status_code == 200
    assert response.json()["user_query"] == "推薦的店"
    assert response.json()["response_type"] == "keyword_search"


def test_search_route_returns_hybrid_response_type_for_dual_execution(
    client, override_api_dep
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(execution_modes=["semantic", "keyword"]),
    )

    response = client.get("/api/v1/property", params={"query": "寵物公園"})

    assert response.status_code == 200
    assert response.json()["user_query"] == "寵物公園"
    assert response.json()["response_type"] == "hybrid_search"


def test_search_route_passes_radius_to_service(client, override_api_dep):
    service = override_api_dep(get_property_service, CapturePropertyService())

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
            "user_coords": None,
            "map_coords": (121.56, 25.03),
            "radius": 2500,
            "open_at_minutes": None,
        }
    ]


def test_nearby_route_expands_category_to_primary_types(client, override_api_dep):
    service = override_api_dep(get_property_service, CapturePropertyService())

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


def test_search_route_includes_has_note_for_authenticated_user(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    service = override_api_dep(
        get_property_service,
        CapturePropertyService(items=[property_entity_factory(identifier="p1")]),
    )
    current_user = user_entity_factory(identifier="u1", name="Ben")
    override_api_dep(get_optional_current_user, current_user)

    response = client.get("/api/v1/property", params={"query": "台北"})

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["id"] == "p1"
    assert data["results"][0]["has_note"] is True
    assert service.calls[-1] == {
        "fn": "get_noted_property_ids",
        "user_id": "u1",
        "property_ids": ["p1"],
    }


def test_search_route_records_history_for_authenticated_user(
    client, override_api_dep, property_entity_factory, user_entity_factory
):
    override_api_dep(
        get_property_service,
        CapturePropertyService(items=[property_entity_factory(identifier="p1")]),
    )
    history_service = override_api_dep(get_user_service, UserServiceStub())
    current_user = user_entity_factory(identifier="u1", name="Ben")
    override_api_dep(get_optional_current_user, current_user)

    response = client.get("/api/v1/property", params={"query": "台北咖啡廳"})

    assert response.status_code == 200
    assert history_service.calls == [
        {
            "user_id": "u1",
            "query": "台北咖啡廳",
            "limit": 20,
        }
    ]


def test_search_route_skips_history_when_user_is_anonymous(client, override_api_dep):
    override_api_dep(get_property_service, CapturePropertyService())
    history_service = override_api_dep(get_user_service, UserServiceStub())

    response = client.get("/api/v1/property", params={"query": "台北咖啡廳"})

    assert response.status_code == 200
    assert history_service.calls == []


def test_create_property_route_returns_property_id_on_success(
    client,
    override_api_dep,
    property_entity_factory,
    anonymous_actor_override,
):
    service = override_api_dep(
        get_property_service,
        CreatePropertyService(
            created_property=property_entity_factory(identifier="p1")
        ),
    )
    override_api_dep(get_optional_request_actor, anonymous_actor_override)

    response = client.post("/api/v1/property", params={"name": "Dessert Cafe"})

    assert response.status_code == 201
    assert response.json() == {"property_id": "p1"}
    assert service.created_property.id == "p1"


def test_create_property_route_returns_409_with_reason_on_failure(
    client,
    override_api_dep,
    anonymous_actor_override,
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

    response = client.post("/api/v1/property", params={"name": "Dessert Cafe"})

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Property is soft-deleted. Restore it before syncing again."
    )


def test_get_detail_returns_404_when_service_has_no_property(client, override_api_dep):
    override_api_dep(get_property_service, MissingDetailService())

    response = client.get("/api/v1/property/missing-id")

    assert response.status_code == 404


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
