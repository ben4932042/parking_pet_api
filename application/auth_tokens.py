from typing import Protocol


class AuthTokenClaims(Protocol):
    @property
    def user_id(self) -> str: ...

    @property
    def source(self) -> str: ...

    @property
    def token_type(self) -> str: ...

    @property
    def session_version(self) -> int: ...


class IAuthTokenService(Protocol):
    def issue_access_token(
        self, *, user_id: str, source: str, session_version: int
    ) -> str: ...

    def issue_refresh_token(
        self, *, user_id: str, source: str, session_version: int
    ) -> str: ...

    def verify_access_token(self, token: str) -> AuthTokenClaims: ...

    def verify_refresh_token(self, token: str) -> AuthTokenClaims: ...
