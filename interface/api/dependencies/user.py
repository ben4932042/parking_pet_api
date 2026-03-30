from typing import Optional

from fastapi import Depends, Header

from application.user import UserService
from domain.entities.audit import ActorInfo, SourceType
from interface.api.dependencies.db import get_user_repository

from infrastructure.mongo.user import UserRepository
from interface.api.exceptions.error import ForbiddenError

from domain.entities.user import UserEntity


def get_user_service(repo=Depends(get_user_repository)) -> UserService:
    return UserService(repo=repo)


def build_actor_from_user(
    current_user: UserEntity, source: SourceType = "user"
) -> ActorInfo:
    return ActorInfo(
        user_id=str(current_user.id),
        name=current_user.name,
        role="user",
        source=source,
    )


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


async def get_optional_current_user(
    x_user_id: Optional[str] = Header(None, description="User ID for authentication"),
    repo: UserRepository = Depends(get_user_repository),
) -> Optional[UserEntity]:
    if not x_user_id:
        return None
    return await repo.get_user_by_id(x_user_id)


async def get_request_actor(
    current_user: UserEntity = Depends(get_current_user),
) -> ActorInfo:
    return build_actor_from_user(current_user)


async def get_optional_request_actor(
    current_user: Optional[UserEntity] = Depends(get_optional_current_user),
) -> ActorInfo:
    if current_user is None:
        return ActorInfo(name="anonymous-api", source="api", role="anonymous")
    return build_actor_from_user(current_user)
