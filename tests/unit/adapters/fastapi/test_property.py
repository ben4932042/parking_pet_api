import pytest

from domain.entities.audit import PropertyAuditAction, PropertyAuditLog
from domain.entities.property import (
    PropertyEntity,
    PropertyFilterCondition,
    PropertyManualOverrides,
    PetFeaturesOverride,
    PetServiceOverride,
)
from domain.entities.property_category import PropertyCategoryKey
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import get_optional_request_actor, get_request_actor
from interface.api.exceptions.error import ConflictError


class CapturePropertyService:
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

    async def update_pet_features(self, property_id, pet_rules, pet_environment, pet_service, actor, reason=None):
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
    return actor_factory(name="anonymous-api", role="anonymous", source="api", user_id=None)


@pytest.fixture
def request_actor_override(actor_factory):
    return actor_factory()


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
    assert service.calls == [
        {
            "q": "dog cafe",
            "user_coords": None,
            "map_coords": (121.56, 25.03),
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


def test_create_property_route_returns_property_id_on_success(
    client,
    override_api_dep,
    property_entity_factory,
    anonymous_actor_override,
):
    service = override_api_dep(
        get_property_service,
        CreatePropertyService(created_property=property_entity_factory(identifier="p1")),
    )
    override_api_dep(get_optional_request_actor, anonymous_actor_override)

    response = client.post("/api/v1/property", params={"name": "Dessert Cafe"})

    assert response.status_code == 201
    assert response.json() == {"property_id": "p1"}
    assert service.created_property.id == "p1"


def test_create_property_route_returns_400_with_reason_on_failure(
    client,
    override_api_dep,
    anonymous_actor_override,
):
    override_api_dep(
        get_property_service,
        CreatePropertyService(error=ConflictError("Property is soft-deleted. Restore it before syncing again.")),
    )
    override_api_dep(get_optional_request_actor, anonymous_actor_override)

    response = client.post("/api/v1/property", params={"name": "Dessert Cafe"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Property is soft-deleted. Restore it before syncing again."


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
    property_entity = property_entity_factory(identifier="p1", place_id="place-1", free_water=False)
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
    service = override_api_dep(get_property_service, PropertyMutationService(property_entity=property_entity))
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
    deleted_property = property_entity_factory(identifier="p1", place_id="place-1").model_copy(
        update={
            "is_deleted": True,
            "deleted_by": request_actor_override,
            "updated_by": request_actor_override,
        }
    )
    service = override_api_dep(get_property_service, PropertyMutationService(property_entity=deleted_property))
    override_api_dep(get_request_actor, request_actor_override)

    response = client.delete("/api/v1/property/p1", params={"reason": "duplicate"})

    assert response.status_code == 200
    data = response.json()
    assert data["property_id"] == "p1"
    assert data["status"] == "deleted"
    assert data["is_deleted"] is True
    assert service.calls[0]["reason"] == "duplicate"


def test_restore_route_returns_restored_status(
    client,
    override_api_dep,
    property_entity_factory,
    request_actor_override,
):
    restored_property = property_entity_factory(identifier="p1", place_id="place-1").model_copy(
        update={
            "is_deleted": False,
            "deleted_by": None,
            "updated_by": request_actor_override,
        }
    )
    service = override_api_dep(get_property_service, PropertyMutationService(property_entity=restored_property))
    override_api_dep(get_request_actor, request_actor_override)

    response = client.post("/api/v1/property/p1/restore", params={"reason": "restore by admin"})

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
            changes={"manual_overrides.pet_features.services.free_water": {"before": False, "after": True}},
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
