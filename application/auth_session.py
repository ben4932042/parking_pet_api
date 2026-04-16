"""Application-layer session lifecycle orchestration for backend auth."""

import hashlib

from pydantic import BaseModel, ConfigDict

from application.auth_tokens import IAuthTokenService
from application.exceptions import AuthenticationError
from domain.entities.user import UserEntity
from domain.repositories.user import IUserRepository


class AuthSession(BaseModel):
    """Backend-issued session payload returned after auth lifecycle actions."""

    access_token: str
    refresh_token: str
    user: UserEntity

    model_config = ConfigDict(frozen=True)


class AuthSessionService:
    """Starts, refreshes, and revokes backend auth sessions."""

    def __init__(
        self,
        *,
        repo: IUserRepository,
        access_token_service: IAuthTokenService,
        refresh_token_service: IAuthTokenService,
    ) -> None:
        self.repo = repo
        self.access_token_service = access_token_service
        self.refresh_token_service = refresh_token_service

    async def start_session(self, *, user: UserEntity) -> AuthSession:
        """Start a new session by rotating persisted session state and tokens."""
        refresh_token = self.refresh_token_service.issue_refresh_token(
            user_id=str(user.id),
            source=user.source,
            session_version=user.session_version + 1,
        )
        session_user = await self.repo.start_auth_session(
            user_id=str(user.id),
            refresh_token_hash=self._hash_token(refresh_token),
        )
        if session_user is None:
            raise AuthenticationError("Invalid authentication credentials")
        return self._build_session(user=session_user, refresh_token=refresh_token)

    async def refresh_session(self, *, refresh_token: str) -> AuthSession:
        """Rotate the refresh token for a valid persisted session."""
        claims = self.refresh_token_service.verify_refresh_token(refresh_token)
        user = await self.repo.get_user_by_id(claims.user_id)
        if (
            user is None
            or user.is_deleted
            or user.source != claims.source
            or user.session_version != claims.session_version
            or user.refresh_token_hash != self._hash_token(refresh_token)
        ):
            raise AuthenticationError("Invalid authentication credentials")

        next_refresh_token = self.refresh_token_service.issue_refresh_token(
            user_id=str(user.id),
            source=user.source,
            session_version=user.session_version,
        )
        refreshed_user = await self.repo.rotate_refresh_token(
            user_id=str(user.id),
            refresh_token_hash=self._hash_token(next_refresh_token),
        )
        if refreshed_user is None:
            raise AuthenticationError("Invalid authentication credentials")
        return self._build_session(
            user=refreshed_user,
            refresh_token=next_refresh_token,
        )

    async def logout(self, *, user_id: str) -> None:
        """Revoke the persisted session for the given user identifier."""
        revoked_user = await self.repo.revoke_auth_session(user_id=user_id)
        if revoked_user is None:
            raise AuthenticationError("Invalid authentication credentials")

    def _build_session(
        self,
        *,
        user: UserEntity,
        refresh_token: str | None = None,
    ) -> AuthSession:
        """Build an auth session payload from persisted user state."""
        access_token = self.access_token_service.issue_access_token(
            user_id=str(user.id),
            source=user.source,
            session_version=user.session_version,
        )
        if refresh_token is None:
            refresh_token = self.refresh_token_service.issue_refresh_token(
                user_id=str(user.id),
                source=user.source,
                session_version=user.session_version,
            )
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user,
        )

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash refresh tokens before they are stored in persistence."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
