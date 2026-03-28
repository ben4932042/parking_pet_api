from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from application.property import PropertyService
from domain.entities import PyObjectId
from interface.api.dependencies.property import get_property_service
from interface.api.schemas.page import Pagination
from interface.api.schemas.property import (
    PropertyDetailResponse,
    PropertyNearbyRequest,
    PropertyOverviewResponse,
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
):
    await service.create_property(name)
