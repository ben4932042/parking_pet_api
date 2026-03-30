from typing import Optional

from fastapi import APIRouter, Depends, Query
from starlette import status

from application.property import PropertyService
from interface.api.dependencies.property import get_property_service
from interface.api.schemas.property import PropertySearchV2Response

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
    response_model=PropertySearchV2Response,
    summary="Search properties by keyword or semantic parsing",
    description=(
        "V2 search keeps the same query interface as v1, but uses a LangGraph-based "
        "router and semantic parsing pipeline before MongoDB retrieval."
    ),
)
async def search_properties_v2(
    query: str = Query(..., description="Natural-language search query."),
    user_lat: float = Query(default=None, description="Current user latitude."),
    user_lng: float = Query(default=None, description="Current user longitude."),
    map_lat: float = Query(default=None, description="Current map center latitude."),
    map_lng: float = Query(default=None, description="Current map center longitude."),
    service: PropertyService = Depends(get_property_service),
):
    items, plan = await service.search_by_keyword_v2(
        q=query,
        user_coords=_coords_or_none(user_lat, user_lng),
        map_coords=_coords_or_none(map_lat, map_lng),
    )
    return {
        "status": "success",
        "route": plan.route,
        "preferences": plan.filter_condition.preferences,
        "semantic_extraction": plan.semantic_extraction,
        "warnings": plan.warnings,
        "used_fallback": plan.used_fallback,
        "fallback_reason": plan.fallback_reason,
        "results": items,
    }
