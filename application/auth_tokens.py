from abc import ABC, abstractmethod


class AuthTokenClaims(ABC):
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
