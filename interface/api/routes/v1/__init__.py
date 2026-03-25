from fastapi import APIRouter

from interface.api.routes.v1.property import router as property_router


router = APIRouter(prefix="/v1")

router.include_router(property_router)
