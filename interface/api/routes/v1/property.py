from fastapi import Depends, APIRouter, HTTPException
from starlette import status

from application.property import PropertyService
from domain.entities import PyObjectId
from interface.api.dependencies.property import get_property_service
from interface.api.schemas.page import PaginationResponse
from interface.api.schemas.property import (
    PropertyDetailResponse,
    PropertyNearbyRequest,
    PropertyKeywordRequest,
)

router = APIRouter(prefix="/property")


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def search_properties_by_keyword(
    params: PropertyKeywordRequest = Depends(),
    service: PropertyService = Depends(get_property_service),
):
    items, total = await service.search_by_keyword(
        params.q, params.type, params.page, params.size
    )
    pages = (total + params.size - 1) // params.size if params.size else 0
    return {"items": items, "total": total, "page": params.page, "size": params.size, "pages": pages}



@router.get(
    "/nearby",
    status_code=status.HTTP_200_OK,
    response_model=PaginationResponse,
)
async def get_nearby_properties(
    params: PropertyNearbyRequest = Depends(),
    service: PropertyService = Depends(get_property_service),
):
    items, total = await service.search_nearby(
        params.lat, params.lng, params.radius, params.type, params.page, params.size
    )
    pages = (total + params.size - 1) // params.size if params.size else 0
    return {"items": items, "total": total, "page": params.page, "size": params.size, "pages": pages}


@router.get("/{property_id}", response_model=PropertyDetailResponse)
async def get_detail(property_id: PyObjectId, service: PropertyService = Depends(get_property_service)):
    prop = await service.get_details(property_id=property_id)
    if not prop:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROPERTY_NOT_FOUND", "message": "Property not found"}})
    return prop