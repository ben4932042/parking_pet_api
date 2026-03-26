from fastapi import APIRouter

from interface.api.routes.v1.property import router as property_router
from interface.api.routes.v1.user import router as user_router


router = APIRouter()

router.include_router(property_router, tags=["property"])
router.include_router(user_router, tags=["user"])
