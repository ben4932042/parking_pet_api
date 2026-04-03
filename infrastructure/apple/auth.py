import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from application.exceptions import AuthenticationError

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


@dataclass(frozen=True)
class AppleIdentity:
    subject: str
    email: str | None = None


class AppleIdentityTokenVerifier:
    def __init__(
        self,
        *,
        bundle_id: str,
        jwks_url: str = APPLE_JWKS_URL,
        issuer: str = APPLE_ISSUER,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.bundle_id = bundle_id.strip()
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.timeout_seconds = timeout_seconds

    async def verify_identity_token(
        self,
        *,
        identity_token: str,
        user_identifier: str,
    ) -> AppleIdentity:
        if not self.bundle_id:
            raise RuntimeError("Apple bundle ID is not configured")

        header, payload, signed_part, signature = self._parse_jwt(identity_token)
        key_id = header.get("kid")
        algorithm = header.get("alg")

        if algorithm != "RS256":
            raise AuthenticationError("Unsupported Apple identity token algorithm")

        jwks = await self._fetch_apple_public_keys()
        public_key = self._build_public_key(jwks=jwks, key_id=key_id)

        try:
            public_key.verify(
                signature,
                signed_part,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception as exc:
            raise AuthenticationError("Invalid Apple identity token signature") from exc

        self._validate_claims(payload=payload, user_identifier=user_identifier)

        return AppleIdentity(
            subject=payload["sub"],
            email=payload.get("email"),
        )

    async def _fetch_apple_public_keys(self) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            return response.json()

    def _validate_claims(self, *, payload: dict, user_identifier: str) -> None:
        issuer = payload.get("iss")
        audience = payload.get("aud")
        subject = payload.get("sub")
        exp = payload.get("exp")
        now_timestamp = datetime.now(UTC).timestamp()

        if issuer != self.issuer:
            raise AuthenticationError("Invalid Apple identity token issuer")
        if audience != self.bundle_id:
            raise AuthenticationError("Invalid Apple identity token audience")
        if not subject:
            raise AuthenticationError("Apple identity token subject is missing")
        if not isinstance(exp, (int, float)) or exp <= now_timestamp:
            raise AuthenticationError("Apple identity token has expired")

        not_before = payload.get("nbf")
        if isinstance(not_before, (int, float)) and not_before > now_timestamp:
            raise AuthenticationError("Apple identity token is not yet valid")

    @staticmethod
    def _build_public_key(*, jwks: dict, key_id: str | None):
        for key in jwks.get("keys", []):
            if key.get("kid") != key_id:
                continue
            if key.get("kty") != "RSA":
                break
            modulus = AppleIdentityTokenVerifier._b64url_to_int(key["n"])
            exponent = AppleIdentityTokenVerifier._b64url_to_int(key["e"])
            return rsa.RSAPublicNumbers(exponent, modulus).public_key()
        raise AuthenticationError("Unable to find matching Apple public key")

    @staticmethod
    def _parse_jwt(token: str) -> tuple[dict, dict, bytes, bytes]:
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Malformed Apple identity token")

        encoded_header, encoded_payload, encoded_signature = parts
        signed_part = f"{encoded_header}.{encoded_payload}".encode("ascii")
        try:
            header = json.loads(
                AppleIdentityTokenVerifier._b64url_decode(encoded_header).decode(
                    "utf-8"
                )
            )
            payload = json.loads(
                AppleIdentityTokenVerifier._b64url_decode(encoded_payload).decode(
                    "utf-8"
                )
            )
            signature = AppleIdentityTokenVerifier._b64url_decode(encoded_signature)
        except Exception as exc:
            raise AuthenticationError("Malformed Apple identity token") from exc

        return header, payload, signed_part, signature

    @staticmethod
    def _b64url_decode(value: str) -> bytes:
        padding_length = (-len(value)) % 4
        return base64.urlsafe_b64decode(value + ("=" * padding_length))

    @staticmethod
    def _b64url_to_int(value: str) -> int:
        return int.from_bytes(AppleIdentityTokenVerifier._b64url_decode(value), "big")
