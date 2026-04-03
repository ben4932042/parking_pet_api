from typing import Optional

from fastapi import Depends, Header

from application.auth_session import AuthSessionService
from application.auth_tokens import IAuthTokenService
from application.apple_auth import AppleAuthService
from application.user import UserService
from domain.entities.audit import ActorInfo, SourceType
from interface.api.dependencies.db import get_user_repository

from infrastructure.apple import AppleIdentityTokenVerifier
from infrastructure.auth import AuthTokenService
from infrastructure.config import settings
from infrastructure.mongo.user import UserRepository
from interface.api.exceptions.error import ForbiddenError, UnauthorizedError

from domain.entities.user import UserEntity


def get_user_service(repo=Depends(get_user_repository)) -> UserService:
    return UserService(repo=repo)


def get_apple_identity_verifier() -> AppleIdentityTokenVerifier:
    return AppleIdentityTokenVerifier(bundle_id=settings.apple.bundle_id)


def get_apple_auth_service(
    repo=Depends(get_user_repository),
    verifier: AppleIdentityTokenVerifier = Depends(get_apple_identity_verifier),
) -> AppleAuthService:
    return AppleAuthService(repo=repo, verifier=verifier)


def get_auth_token_service() -> IAuthTokenService:
    return AuthTokenService(
        signing_key=settings.auth.signing_key.get_secret_value(),
        ttl_seconds=settings.auth.access_token_ttl_seconds,
        issuer=settings.auth.issuer,
    )


def get_refresh_token_service() -> IAuthTokenService:
    return AuthTokenService(
        signing_key=settings.auth.signing_key.get_secret_value(),
        ttl_seconds=settings.auth.refresh_token_ttl_seconds,
        issuer=settings.auth.issuer,
    )


def get_auth_session_service(
    repo=Depends(get_user_repository),
    access_token_service: IAuthTokenService = Depends(get_auth_token_service),
    refresh_token_service: IAuthTokenService = Depends(get_refresh_token_service),
) -> AuthSessionService:
    # Access and refresh tokens share the same signer but use different TTLs.
    return AuthSessionService(
        repo=repo,
        access_token_service=access_token_service,
        refresh_token_service=refresh_token_service,
    )


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
    authorization: Optional[str] = Header(
        None, description="Bearer token for authenticated users"
    ),
    repo: UserRepository = Depends(get_user_repository),
    token_service: IAuthTokenService = Depends(get_auth_token_service),
) -> UserEntity:
    if not authorization:
        raise ForbiddenError("Authentication required")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise UnauthorizedError("Invalid authorization header")
    claims = token_service.verify_access_token(credentials.strip())
    current_user = await repo.get_user_by_id(claims.user_id)
    if (
        not current_user
        or current_user.source != claims.source
        or current_user.session_version != claims.session_version
    ):
        raise UnauthorizedError("Invalid authentication credentials")
    if current_user.is_deleted:
        raise UnauthorizedError("Invalid authentication credentials")
    return current_user


async def get_optional_current_user(
    authorization: Optional[str] = Header(
        None, description="Bearer token for authenticated users"
    ),
    repo: UserRepository = Depends(get_user_repository),
    token_service: IAuthTokenService = Depends(get_auth_token_service),
) -> Optional[UserEntity]:
    if not authorization:
        return None
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise UnauthorizedError("Invalid authorization header")
    claims = token_service.verify_access_token(credentials.strip())
    current_user = await repo.get_user_by_id(claims.user_id)
    if (
        current_user is None
        or current_user.is_deleted
        or current_user.source != claims.source
        or current_user.session_version != claims.session_version
    ):
        raise UnauthorizedError("Invalid authentication credentials")
    return current_user


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
