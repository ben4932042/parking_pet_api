import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from application.exceptions import AuthenticationError


@dataclass(frozen=True)
class AuthTokenClaims:
    user_id: str
    source: str
    token_type: str
    session_version: int


class AuthTokenService:
    def __init__(
        self,
        *,
        signing_key: str,
        ttl_seconds: int,
        issuer: str,
    ) -> None:
        self.signing_key = signing_key.encode("utf-8")
        self.ttl_seconds = ttl_seconds
        self.issuer = issuer

    def issue_access_token(
        self, *, user_id: str, source: str, session_version: int
    ) -> str:
        return self._issue_token(
            user_id=user_id,
            source=source,
            session_version=session_version,
            token_type="access",
        )

    def issue_refresh_token(
        self, *, user_id: str, source: str, session_version: int
    ) -> str:
        return self._issue_token(
            user_id=user_id,
            source=source,
            session_version=session_version,
            token_type="refresh",
        )

    def _issue_token(
        self,
        *,
        user_id: str,
        source: str,
        session_version: int,
        token_type: str,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": user_id,
            "source": source,
            "type": token_type,
            "sv": session_version,
            "iss": self.issuer,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.ttl_seconds)).timestamp()),
        }
        encoded_payload = self._b64url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = self._sign(encoded_payload)
        return f"{encoded_payload}.{signature}"

    def verify_access_token(self, token: str) -> AuthTokenClaims:
        return self._verify_token(token, expected_type="access")

    def verify_refresh_token(self, token: str) -> AuthTokenClaims:
        return self._verify_token(token, expected_type="refresh")

    def _verify_token(self, token: str, *, expected_type: str) -> AuthTokenClaims:
        parts = token.split(".")
        if len(parts) != 2:
            raise AuthenticationError("Malformed access token")

        encoded_payload, signature = parts
        expected_signature = self._sign(encoded_payload)
        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationError("Invalid access token signature")

        try:
            payload = json.loads(self._b64url_decode(encoded_payload).decode("utf-8"))
        except Exception as exc:
            raise AuthenticationError("Malformed access token") from exc

        if payload.get("iss") != self.issuer:
            raise AuthenticationError("Invalid access token issuer")

        exp = payload.get("exp")
        if not isinstance(exp, int) or exp <= int(datetime.now(UTC).timestamp()):
            raise AuthenticationError("Access token has expired")

        user_id = payload.get("sub")
        source = payload.get("source")
        token_type = payload.get("type")
        session_version = payload.get("sv")
        if not isinstance(user_id, str) or not user_id.strip():
            raise AuthenticationError("Access token subject is missing")
        if not isinstance(source, str) or not source.strip():
            raise AuthenticationError("Access token source is missing")
        if token_type != expected_type:
            raise AuthenticationError("Invalid access token type")
        if not isinstance(session_version, int) or session_version < 0:
            raise AuthenticationError("Access token session version is missing")

        return AuthTokenClaims(
            user_id=user_id,
            source=source,
            token_type=token_type,
            session_version=session_version,
        )

    def _sign(self, encoded_payload: str) -> str:
        digest = hmac.new(
            self.signing_key,
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return self._b64url_encode(digest)

    @staticmethod
    def _b64url_encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    @staticmethod
    def _b64url_decode(value: str) -> bytes:
        padding_length = (-len(value)) % 4
        return base64.urlsafe_b64decode(value + ("=" * padding_length))
