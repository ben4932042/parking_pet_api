from typing import Optional

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.auth_session import AuthSessionService
from application.auth_tokens import IAuthTokenService
from application.apple_auth import AppleAuthService, IAppleIdentityVerifier
from application.exceptions import AuthenticationError as ApplicationAuthenticationError
from application.user import UserService
from domain.entities.audit import ActorInfo, SourceType
from interface.api.dependencies.db import get_user_repository
from interface.api.logging_utils import log_api_event

from infrastructure.apple import AppleIdentityTokenVerifier
from infrastructure.auth import AuthTokenService
from infrastructure.config import settings
from infrastructure.mongo.user import UserRepository
from interface.api.exceptions.error import ForbiddenError, UnauthorizedError

from domain.entities.user import UserEntity

bearer_auth_optional = HTTPBearer(auto_error=False)
bearer_auth_required = HTTPBearer(auto_error=False)


def get_user_service(repo=Depends(get_user_repository)) -> UserService:
    return UserService(repo=repo)


def get_apple_identity_verifier() -> AppleIdentityTokenVerifier:
    return AppleIdentityTokenVerifier(bundle_id=settings.apple.bundle_id)


def get_apple_auth_service(
    repo=Depends(get_user_repository),
    verifier: IAppleIdentityVerifier = Depends(get_apple_identity_verifier),
) -> AppleAuthService:
    return AppleAuthService(repo=repo, verifier=verifier)


def get_auth_token_service() -> AuthTokenService:
    return AuthTokenService(
        signing_key=settings.auth.signing_key.get_secret_value(),
        ttl_seconds=settings.auth.access_token_ttl_seconds,
        issuer=settings.auth.issuer,
    )


def get_refresh_token_service() -> AuthTokenService:
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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(
        bearer_auth_required
    ),
    repo: UserRepository = Depends(get_user_repository),
    token_service: IAuthTokenService = Depends(get_auth_token_service),
) -> UserEntity:
    if credentials is None or not credentials.credentials.strip():
        raise ForbiddenError("Authentication required")
    if credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Invalid authorization header")
    try:
        claims = token_service.verify_access_token(credentials.credentials.strip())
    except ApplicationAuthenticationError as exc:
        log_api_event(
            "auth_invalid_token",
            request=request,
            level=30,
            extra={
                "path": request.url.path,
                "reason": exc.message or "invalid_access_token",
            },
        )
        raise UnauthorizedError("Invalid authentication credentials") from exc
    current_user = await repo.get_user_by_id(claims.user_id)
    if current_user is None or current_user.source != claims.source:
        log_api_event(
            "auth_invalid_token",
            request=request,
            user_id=claims.user_id,
            level=30,
            extra={
                "path": request.url.path,
                "reason": "invalid_authentication_credentials",
            },
        )
        raise UnauthorizedError("Invalid authentication credentials")
    if current_user.is_deleted:
        log_api_event(
            "auth_invalid_token",
            request=request,
            user_id=claims.user_id,
            level=30,
            extra={
                "path": request.url.path,
                "reason": "deleted_user",
            },
        )
        raise UnauthorizedError("Invalid authentication credentials")
    if current_user.session_version != claims.session_version:
        log_api_event(
            "auth_session_mismatch",
            request=request,
            user_id=str(current_user.id),
            level=30,
            extra={
                "path": request.url.path,
                "token_session_version": claims.session_version,
                "current_session_version": current_user.session_version,
            },
        )
        raise UnauthorizedError("Invalid authentication credentials")
    request.state.user_id = str(current_user.id)
    request.state.user_source = current_user.source
    request.state.session_version = current_user.session_version
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(
        bearer_auth_optional
    ),
    repo: UserRepository = Depends(get_user_repository),
    token_service: IAuthTokenService = Depends(get_auth_token_service),
) -> Optional[UserEntity]:
    if credentials is None:
        return None
    if credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise UnauthorizedError("Invalid authorization header")
    try:
        claims = token_service.verify_access_token(credentials.credentials.strip())
    except ApplicationAuthenticationError as exc:
        log_api_event(
            "auth_invalid_token",
            request=request,
            level=30,
            extra={
                "path": request.url.path,
                "reason": exc.message or "invalid_access_token",
            },
        )
        raise UnauthorizedError("Invalid authentication credentials") from exc
    current_user = await repo.get_user_by_id(claims.user_id)
    if current_user is None or current_user.source != claims.source:
        log_api_event(
            "auth_invalid_token",
            request=request,
            user_id=claims.user_id,
            level=30,
            extra={
                "path": request.url.path,
                "reason": "invalid_authentication_credentials",
            },
        )
        raise UnauthorizedError("Invalid authentication credentials")
    if current_user.is_deleted:
        log_api_event(
            "auth_invalid_token",
            request=request,
            user_id=claims.user_id,
            level=30,
            extra={
                "path": request.url.path,
                "reason": "deleted_user",
            },
        )
        raise UnauthorizedError("Invalid authentication credentials")
    if current_user.session_version != claims.session_version:
        log_api_event(
            "auth_session_mismatch",
            request=request,
            user_id=str(current_user.id),
            level=30,
            extra={
                "path": request.url.path,
                "token_session_version": claims.session_version,
                "current_session_version": current_user.session_version,
            },
        )
        raise UnauthorizedError("Invalid authentication credentials")
    request.state.user_id = str(current_user.id)
    request.state.user_source = current_user.source
    request.state.session_version = current_user.session_version
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
