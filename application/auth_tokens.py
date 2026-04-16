"""Abstract token contracts shared by application auth workflows."""

from abc import ABC, abstractmethod


class AuthTokenClaims(ABC):
    """Minimal claim set required by application session validation."""

    @property
    @abstractmethod
    def user_id(self) -> str: ...

    @property
    @abstractmethod
    def source(self) -> str: ...

    @property
    @abstractmethod
    def token_type(self) -> str: ...

    @property
    @abstractmethod
    def session_version(self) -> int: ...


class IAuthTokenService(ABC):
    """Issues and verifies backend auth tokens for one token class."""

    @abstractmethod
    def issue_access_token(
        self, *, user_id: str, source: str, session_version: int
    ) -> str: ...

    @abstractmethod
    def issue_refresh_token(
        self, *, user_id: str, source: str, session_version: int
    ) -> str: ...

    @abstractmethod
    def verify_access_token(self, token: str) -> AuthTokenClaims: ...

    @abstractmethod
    def verify_refresh_token(self, token: str) -> AuthTokenClaims: ...
