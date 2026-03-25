from typing import Optional

from fastapi import Depends, APIRouter, BackgroundTasks, HTTPException
from starlette import status

from application.property import PropertyService
from domain.entities import PyObjectId
from interface.api.dependencies.property import get_property_service
from interface.api.schemas.property import PropertyListResponse, PropertyNearbyRequest

router = APIRouter(prefix="/property")


@router.get(
    "/nearby",
    status_code=status.HTTP_200_OK,
    response_model=PropertyListResponse,
)
async def get_nearby_properties(
    params: PropertyNearbyRequest = Depends(),
    service: PropertyService = Depends(get_property_service),
):
    properties = await service.search_properties(params.lat, params.lng, params.radius, params.q, params.type)
    return {"properties": properties}

@router.get("/{property_id}", response_model=PropertyListResponse)
async def get_detail(property_id: PyObjectId, service: PropertyService = Depends(get_property_service)):
    prop = await service.get_details(property_id=property_id)
    if not prop:
        raise HTTPException(status_code=404, detail={"error": {"code": "PROPERTY_NOT_FOUND", "message": "Property not found"}})
    return {"properties": [prop]}