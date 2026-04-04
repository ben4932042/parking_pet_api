import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from application.exceptions import ApplicationError
from application.property import PropertyService
from application.property_note import PropertyNoteService
from application.user import UserService
from domain.entities.audit import ActorInfo
from domain.entities import PyObjectId
from domain.entities.property import (
    PetEnvironmentOverride,
    PetRulesOverride,
    PetServiceOverride,
)
from domain.entities.property_category import get_primary_types_by_category_key
from domain.entities.property_category import PropertyCategoryKey
from domain.entities.user import UserEntity
from interface.api.exceptions.error import AppError, from_application_error
from interface.api.dependencies.property_note import get_property_note_service
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_current_user,
    get_optional_current_user,
    get_optional_request_actor,
    get_request_actor,
    get_user_service,
)
from interface.api.schemas.page import Pagination
from interface.api.schemas.property_note import (
    PropertyNoteResponse,
    PropertyNoteUpsertRequest,
)
from interface.api.schemas.property import (
    PropertyAuditLogResponse,
    PropertyAliasesPatchRequest,
    PropertyAliasesResponse,
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
logger = logging.getLogger(__name__)


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
    summary="Search properties",
    description=(
        "Search properties with the semantic pipeline while preserving the current response shape. "
        "Optional user/map coordinates help the backend apply geo-aware filtering and reranking."
    ),
)
async def search_properties_by_keyword(
    query: str = Query(..., description="Natural-language search query."),
    category: PropertyCategoryKey | None = Query(
        default=None,
        description="Optional frontend category selector. When provided, search uses keyword-only mode.",
    ),
    user_lat: float = Query(default=None, description="Current user latitude."),
    user_lng: float = Query(default=None, description="Current user longitude."),
    map_lat: float = Query(default=None, description="Current map center latitude."),
    map_lng: float = Query(default=None, description="Current map center longitude."),
    radius: int = Query(
        default=None,
        ge=1,
        description=(
            "Optional map-driven search radius in meters. "
            "Used only when the query does not already express an explicit distance condition "
            "and does not already contain an explicit landmark/address anchor."
        ),
    ),
    service: PropertyService = Depends(get_property_service),
    user_service: UserService = Depends(get_user_service),
    current_user: Optional[UserEntity] = Depends(get_optional_current_user),
):
    result = await service.search_properties(
        q=query,
        category=category,
        user_coords=_coords_or_none(user_lat, user_lng),
        map_coords=_coords_or_none(map_lat, map_lng),
        radius=radius,
        current_user=current_user,
    )
    if current_user is not None:
        try:
            await user_service.record_recent_search(
                user_id=str(current_user.id),
                query=query,
            )
        except Exception:
            logger.exception(
                "Failed to record search history",
                extra={"user_id": str(current_user.id), "query": query},
            )
    return result


@router.get(
    "/{property_id}/note",
    status_code=status.HTTP_200_OK,
    response_model=PropertyNoteResponse | None,
    summary="Get my private note for a property",
)
async def get_property_note(
    property_id: PyObjectId,
    service: PropertyNoteService = Depends(get_property_note_service),
    current_user: UserEntity = Depends(get_current_user),
):
    note = await service.get_note(str(current_user.id), property_id)
    if note is None:
        return None
    return PropertyNoteResponse(
        property_id=note.property_id,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.put(
    "/{property_id}/note",
    status_code=status.HTTP_200_OK,
    response_model=PropertyNoteResponse,
    summary="Create or update my private note for a property",
)
async def upsert_property_note(
    property_id: PyObjectId,
    payload: PropertyNoteUpsertRequest,
    service: PropertyNoteService = Depends(get_property_note_service),
    current_user: UserEntity = Depends(get_current_user),
):
    note = await service.save_note(str(current_user.id), property_id, payload.content)
    return PropertyNoteResponse(
        property_id=note.property_id,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete(
    "/{property_id}/note",
    status_code=status.HTTP_200_OK,
    summary="Delete my private note for a property",
)
async def delete_property_note(
    property_id: PyObjectId,
    service: PropertyNoteService = Depends(get_property_note_service),
    current_user: UserEntity = Depends(get_current_user),
):
    deleted = await service.delete_note(str(current_user.id), property_id)
    return {"property_id": property_id, "deleted": deleted}


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
    current_user: Optional[UserEntity] = Depends(get_optional_current_user),
):
    types = (
        get_primary_types_by_category_key(params.category) if params.category else []
    )
    items, total = await service.get_nearby_overviews(
        params.lat,
        params.lng,
        params.radius,
        types,
        params.page,
        params.size,
        current_user=current_user,
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
    except ApplicationError as exc:
        api_error = exc if isinstance(exc, AppError) else from_application_error(exc)
        raise HTTPException(
            status_code=api_error.http_status,
            detail=api_error.message or "Failed to create property.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=str(exc) or "Failed to create property."
        )


@router.post(
    "/{property_id}/renew",
    status_code=status.HTTP_200_OK,
    response_model=PropertyMutationResponse,
    summary="Renew property from Google Places",
    description=(
        "Refreshes an existing property by property_id. "
        "Use `basic` mode to restart from Places Text Search Enterprise + Atmosphere and then Places Details Enterprise + Atmosphere. "
        "Use `details` mode to refresh only from Places Details Enterprise + Atmosphere using the existing raw source snapshot."
    ),
)
async def renew_property(
    property_id: PyObjectId,
    mode: str = Query(
        ...,
        description=(
            "`basic` refreshes from Places Text Search Enterprise + Atmosphere and then Places Details Enterprise + Atmosphere. "
            "`details` refreshes only the detail fields from Places Details Enterprise + Atmosphere using the existing raw source snapshot."
        ),
    ),
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    return await service.renew_property_result(
        property_id=property_id,
        mode=mode,
        actor=actor,
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
        pet_rules=(
            PetRulesOverride(**payload.pet_rules.model_dump())
            if payload.pet_rules
            else None
        ),
        pet_environment=(
            PetEnvironmentOverride(**payload.pet_environment.model_dump())
            if payload.pet_environment
            else None
        ),
        pet_service=(
            PetServiceOverride(**payload.pet_service.model_dump())
            if payload.pet_service
            else None
        ),
        actor=actor,
        reason=payload.reason,
    )
    return updated_property


@router.patch(
    "/{property_id}/aliases",
    status_code=status.HTTP_200_OK,
    response_model=PropertyAliasesResponse,
    summary="Patch manual aliases for property search",
    description=(
        "Replace the manual alias list for a property. "
        "The backend regenerates normalized aliases in the same update."
    ),
)
async def update_property_aliases(
    property_id: PyObjectId,
    payload: PropertyAliasesPatchRequest,
    service: PropertyService = Depends(get_property_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    updated_property = await service.update_aliases(
        property_id=property_id,
        manual_aliases=payload.manual_aliases,
        actor=actor,
        reason=payload.reason,
    )
    return updated_property


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
    return await service.soft_delete_property(
        property_id=property_id,
        actor=actor,
        reason=reason,
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
    return await service.restore_property(
        property_id=property_id,
        actor=actor,
        reason=reason,
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
