from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from application.property import PropertyService
from domain.entities.audit import ActorInfo
from domain.entities import PyObjectId
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import get_optional_request_actor, get_request_actor
from interface.api.schemas.page import Pagination
from interface.api.schemas.property import (
    PropertyAuditLogResponse,
    PropertyDetailResponse,
    PropertyMutationResponse,
    PropertyNearbyRequest,
    PropertyOverviewResponse,
    PropertyPetFeaturesPatchRequest,
    PropertyPetFeaturesResponse,
    PropertySearchResponse,
)

router = APIRouter(prefix="/property")


def _coords_or_none(lat: Optional[float], lng: Optional[float]) -> Optional[tuple[float, float]]:
    if lat is None or lng is None:
        return None
    return (lng, lat)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PropertySearchResponse,
)
async def search_properties_by_keyword(
    query: str,
    user_lat: float = None,
    user_lng: float = None,
    map_lat: float = None,
    map_lng: float = None,
    service: PropertyService = Depends(get_property_service),
):
    items, conditions = await service.search_by_keyword(
        q=query,
        user_coords=_coords_or_none(user_lat, user_lng),
        map_coords=_coords_or_none(map_lat, map_lng),
    )
    return {"status": "success", "preferences": conditions.preferences, "results": items}


@router.get(
    "/nearby",
    status_code=status.HTTP_200_OK,
    response_model=Pagination[PropertyOverviewResponse],
)
async def get_nearby_properties(
    params: PropertyNearbyRequest = Depends(),
    service: PropertyService = Depends(get_property_service),
):
    types = params.types_str.split(",") if params.types_str else []
    items, total = await service.search_nearby(
        params.lat, params.lng, params.radius, types, params.page, params.size
    )
    pages = (total + params.size - 1) // params.size if params.size else 0
    return {"items": items, "total": total, "page": params.page, "size": params.size, "pages": pages}


@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_detail(property_id: PyObjectId, service: PropertyService = Depends(get_property_service)):
    prop = await service.get_details(property_id=property_id)
    if prop is None:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "PROPERTY_NOT_FOUND", "message": "Property not found"}},
        )
    return prop


@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
async def create_property(
    name: str,
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_optional_request_actor),
):
    await service.create_property(name, actor=actor)


@router.patch(
    "/{property_id}/pet-features",
    status_code=status.HTTP_200_OK,
    response_model=PropertyPetFeaturesResponse,
)
async def update_property_pet_features(
    property_id: PyObjectId,
    payload: PropertyPetFeaturesPatchRequest,
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    updated_property = await service.update_pet_features(
        property_id=property_id,
        pet_rules=payload.pet_rules,
        pet_environment=payload.pet_environment,
        pet_service=payload.pet_service,
        actor=actor,
        reason=payload.reason,
    )
    return PropertyPetFeaturesResponse(
        property_id=updated_property.id,
        inferred_pet_features=updated_property.ai_analysis.pet_features,
        manual_pet_features=(
            updated_property.manual_overrides.pet_features
            if updated_property.manual_overrides
            else None
        ),
        effective_pet_features=updated_property.effective_pet_features,
        updated_by=updated_property.updated_by,
        updated_at=updated_property.updated_at,
        reason=updated_property.manual_overrides.reason if updated_property.manual_overrides else None,
    )


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=PropertyMutationResponse,
)
async def soft_delete_property(
    property_id: PyObjectId,
    reason: Optional[str] = None,
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    deleted_property = await service.soft_delete_property(
        property_id=property_id,
        actor=actor,
        reason=reason,
    )
    return PropertyMutationResponse(
        property_id=deleted_property.id,
        status="deleted",
        is_deleted=deleted_property.is_deleted,
        updated_by=deleted_property.updated_by,
        updated_at=deleted_property.updated_at,
        deleted_by=deleted_property.deleted_by,
        deleted_at=deleted_property.deleted_at,
    )


@router.post(
    "/{property_id}/restore",
    status_code=status.HTTP_200_OK,
    response_model=PropertyMutationResponse,
)
async def restore_property(
    property_id: PyObjectId,
    reason: Optional[str] = None,
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    restored_property = await service.restore_property(
        property_id=property_id,
        actor=actor,
        reason=reason,
    )
    return PropertyMutationResponse(
        property_id=restored_property.id,
        status="restored",
        is_deleted=restored_property.is_deleted,
        updated_by=restored_property.updated_by,
        updated_at=restored_property.updated_at,
        deleted_by=restored_property.deleted_by,
        deleted_at=restored_property.deleted_at,
    )


@router.get(
    "/{property_id}/audit-logs",
    status_code=status.HTTP_200_OK,
    response_model=list[PropertyAuditLogResponse],
)
async def list_property_audit_logs(
    property_id: PyObjectId,
    limit: int = 50,
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    _ = actor
    return await service.get_audit_logs(property_id=property_id, limit=limit)
