from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from application.property import PropertyService
from domain.entities.audit import ActorInfo
from domain.entities import PyObjectId
from domain.entities.property_category import get_primary_types_by_category_key
from interface.api.exceptions.error import AppError
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_optional_request_actor,
    get_request_actor,
)
from interface.api.schemas.page import Pagination
from interface.api.schemas.property import (
    PropertyAuditLogResponse,
    PropertyCreateResponse,
    PropertyDetailResponse,
    PropertyMutationResponse,
    PropertyNearbyRequest,
    PropertyOverviewResponse,
    PropertyPetFeaturesPatchRequest,
    PropertyPetFeaturesResponse,
    PropertySearchResponse,
)

router = APIRouter(prefix="/property")


def _coords_or_none(
    lat: Optional[float], lng: Optional[float]
) -> Optional[tuple[float, float]]:
    if lat is None or lng is None:
        return None
    return lng, lat


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PropertySearchResponse,
    summary="Search properties by keyword",
    description=(
        "Search properties by natural-language keyword. "
        "Optional user/map coordinates help the backend apply geo-aware filtering and reranking."
    ),
)
async def search_properties_by_keyword(
    query: str = Query(..., description="Natural-language search query."),
    user_lat: float = Query(default=None, description="Current user latitude."),
    user_lng: float = Query(default=None, description="Current user longitude."),
    map_lat: float = Query(default=None, description="Current map center latitude."),
    map_lng: float = Query(default=None, description="Current map center longitude."),
    service: PropertyService = Depends(get_property_service),
):
    items, conditions = await service.search_by_keyword(
        q=query,
        user_coords=_coords_or_none(user_lat, user_lng),
        map_coords=_coords_or_none(map_lat, map_lng),
    )
    return {
        "status": "success",
        "preferences": conditions.preferences,
        "results": items,
    }


@router.get(
    "/nearby",
    status_code=status.HTTP_200_OK,
    response_model=Pagination[PropertyOverviewResponse],
    summary="Get nearby properties",
    description=(
        "Nearby search based on latitude/longitude and radius. "
        "Use the category enum instead of raw primary_type strings. "
        "The backend expands category into the corresponding Google Places primary_type set."
    ),
)
async def get_nearby_properties(
    params: PropertyNearbyRequest = Depends(),
    service: PropertyService = Depends(get_property_service),
):
    types = (
        get_primary_types_by_category_key(params.category) if params.category else []
    )
    items, total = await service.search_nearby(
        params.lat, params.lng, params.radius, types, params.page, params.size
    )
    pages = (total + params.size - 1) // params.size if params.size else 0
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages,
    }


@router.get(
    "/{property_id}",
    response_model=PropertyDetailResponse,
    summary="Get property detail",
    description="Returns a single property detail record. Soft-deleted properties are not returned from this endpoint.",
)
async def get_detail(
    property_id: PyObjectId, service: PropertyService = Depends(get_property_service)
):
    prop = await service.get_details(property_id=property_id)
    if prop is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {"code": "PROPERTY_NOT_FOUND", "message": "Property not found"}
            },
        )
    return prop


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PropertyCreateResponse,
    summary="Create or sync property by keyword",
    description=(
        "Creates a new property from a keyword/name lookup or syncs an existing property if the resolved place already exists. "
        "Successful requests return HTTP 201 with the property ID. "
        "Failures return HTTP 400 with a readable reason. "
        "Manual pet-feature overrides are preserved during sync."
    ),
)
async def create_property(
    name: str = Query(
        ...,
        description="Property keyword or business name used for Google Places lookup.",
    ),
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_optional_request_actor),
):
    try:
        created_property = await service.create_property(name, actor=actor)
        return PropertyCreateResponse(property_id=created_property.id)
    except AppError as exc:
        raise HTTPException(
            status_code=400, detail=exc.message or "Failed to create property."
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=str(exc) or "Failed to create property."
        )


@router.patch(
    "/{property_id}/pet-features",
    status_code=status.HTTP_200_OK,
    response_model=PropertyPetFeaturesResponse,
    summary="Patch manual pet-feature overrides",
    description=(
        "Partial update for manual pet-feature overrides. "
        "Only send the fields that need to change. "
        "Omitted fields remain unchanged."
    ),
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
        reason=updated_property.manual_overrides.reason
        if updated_property.manual_overrides
        else None,
    )


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=PropertyMutationResponse,
    summary="Soft delete property",
    description="Marks a property as deleted. Soft-deleted properties are excluded from normal search and detail endpoints.",
)
async def soft_delete_property(
    property_id: PyObjectId,
    reason: Optional[str] = Query(
        default=None, description="Optional audit reason for the soft delete."
    ),
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
    summary="Restore soft-deleted property",
    description="Restores a previously soft-deleted property so it becomes visible in normal APIs again.",
)
async def restore_property(
    property_id: PyObjectId,
    reason: Optional[str] = Query(
        default=None, description="Optional audit reason for the restore action."
    ),
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
    summary="List property audit logs",
    description="Returns audit history for create, sync, pet-feature override, soft delete, and restore actions.",
)
async def list_property_audit_logs(
    property_id: PyObjectId,
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of audit log records to return.",
    ),
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    _ = actor
    return await service.get_audit_logs(property_id=property_id, limit=limit)
