from fastapi import Depends

from application.user import UserService
from interface.api.dependencies.db import get_user_repository
from typing import Optional
from fastapi import Header

from infrastructure.mongo.user import UserRepository
from interface.api.exceptions.error import ForbiddenError

from domain.entities.user import UserEntity


def get_user_service(repo=Depends(get_user_repository)) -> UserService:
    return UserService(repo=repo)


async def get_current_user(
    x_user_id: Optional[str] = Header(None, description="User ID for authentication"),
    repo: UserRepository = Depends(get_user_repository),
) -> UserEntity:
    if not x_user_id:
        raise ForbiddenError("Authentication required")
    current_user = await repo.get_user_by_id(x_user_id)

    if not current_user:
        raise ForbiddenError("Invalid authentication credentials")

    return current_user
