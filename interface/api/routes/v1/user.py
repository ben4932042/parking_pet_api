from fastapi import Depends, APIRouter
from starlette import status

from application.user import UserService
from interface.api.dependencies.user import get_user_service, get_current_user

from interface.api.schemas.user import UserDetailResponse

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
