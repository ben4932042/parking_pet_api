from fastapi import Depends, APIRouter
from starlette import status

from application.property import PropertyService
from application.user import UserService
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import get_user_service, get_current_user

from domain.entities import PyObjectId
from interface.api.schemas.property import PropertyOverviewResponse
from interface.api.schemas.user import (
    UserDetailResponse,
    FavoritePropertyResponse,
    FavoritePropertyStatusResponse,
)

router = APIRouter(prefix="/user")


@router.post(
    "/login", status_code=status.HTTP_200_OK, response_model=UserDetailResponse
)
async def create_new_user(
    username: str,
    service: UserService = Depends(get_user_service),
):
    return await service.basic_sign_in(name=username)


@router.patch(
    "/profile", status_code=status.HTTP_201_CREATED, response_model=UserDetailResponse
)
async def update_user_profile(
    name: str,
    service: UserService = Depends(get_user_service),
    current_user=Depends(get_current_user),
):
    return await service.update_user_profile(user_id=current_user.id, name=name)


@router.get("/me", status_code=status.HTTP_200_OK, response_model=UserDetailResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.put(
    "/favorite/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=FavoritePropertyResponse,
)
async def update_user_favorite_property(
    property_id: PyObjectId,
    is_favorite: bool,
    service: UserService = Depends(get_user_service),
    current_user=Depends(get_current_user),
):
    user = await service.update_favorite_property(
        user_id=current_user.id,
        property_id=property_id,
        is_favorite=is_favorite,
    )
    return FavoritePropertyResponse(
        **user.model_dump(by_alias=True),
        property_id=property_id,
        is_favorite=is_favorite,
    )


@router.get(
    "/favorite/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=FavoritePropertyStatusResponse,
)
async def get_user_favorite_property_status(
    property_id: PyObjectId,
    current_user=Depends(get_current_user),
):
    return FavoritePropertyStatusResponse(
        property_id=property_id,
        is_favorite=property_id in current_user.favorite_property_ids,
    )


@router.get(
    "/favorite",
    status_code=status.HTTP_200_OK,
    response_model=list[PropertyOverviewResponse],
)
async def get_user_favorite_properties(
    current_user=Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service),
):
    return await property_service.get_overviews_by_ids(
        current_user.favorite_property_ids
    )
