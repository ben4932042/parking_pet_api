import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from application.exceptions import AuthenticationError
from infrastructure.apple.auth import AppleIdentityTokenVerifier


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _build_token(private_key, *, payload: dict, key_id: str = "test-key") -> str:
    header = {"alg": "RS256", "kid": key_id, "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def _public_jwk(public_key, *, key_id: str = "test-key") -> dict:
    public_numbers = public_key.public_numbers()
    modulus = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    exponent = public_numbers.e.to_bytes(
        (public_numbers.e.bit_length() + 7) // 8, "big"
    )
    return {
        "kty": "RSA",
        "kid": key_id,
        "alg": "RS256",
        "use": "sig",
        "n": _b64url_encode(modulus),
        "e": _b64url_encode(exponent),
    }


@pytest.mark.asyncio
async def test_verify_identity_token_accepts_valid_apple_token(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = _public_jwk(private_key.public_key())
    payload = {
        "iss": "https://appleid.apple.com",
        "aud": "com.example.petapp",
        "sub": "apple-sub-1",
        "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        "email": "ben@example.com",
    }
    token = _build_token(private_key, payload=payload)
    verifier = AppleIdentityTokenVerifier(bundle_id="com.example.petapp")

    async def _fake_fetch_keys():
        return {"keys": [public_jwk]}

    monkeypatch.setattr(verifier, "_fetch_apple_public_keys", _fake_fetch_keys)

    identity = await verifier.verify_identity_token(
        identity_token=token,
        user_identifier="apple-user-1",
    )

    assert identity.subject == "apple-sub-1"
    assert identity.email == "ben@example.com"


@pytest.mark.asyncio
async def test_verify_identity_token_rejects_wrong_audience(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = _public_jwk(private_key.public_key())
    payload = {
        "iss": "https://appleid.apple.com",
        "aud": "com.example.otherapp",
        "sub": "apple-sub-1",
        "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
    }
    token = _build_token(private_key, payload=payload)
    verifier = AppleIdentityTokenVerifier(bundle_id="com.example.petapp")

    async def _fake_fetch_keys():
        return {"keys": [public_jwk]}

    monkeypatch.setattr(verifier, "_fetch_apple_public_keys", _fake_fetch_keys)

    with pytest.raises(AuthenticationError) as exc_info:
        await verifier.verify_identity_token(
            identity_token=token,
            user_identifier="apple-user-1",
        )

    assert exc_info.value.message == "Invalid Apple identity token audience"


@pytest.mark.asyncio
async def test_verify_identity_token_rejects_expired_token(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = _public_jwk(private_key.public_key())
    payload = {
        "iss": "https://appleid.apple.com",
        "aud": "com.example.petapp",
        "sub": "apple-sub-1",
        "exp": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
    }
    token = _build_token(private_key, payload=payload)
    verifier = AppleIdentityTokenVerifier(bundle_id="com.example.petapp")

    async def _fake_fetch_keys():
        return {"keys": [public_jwk]}

    monkeypatch.setattr(verifier, "_fetch_apple_public_keys", _fake_fetch_keys)

    with pytest.raises(AuthenticationError) as exc_info:
        await verifier.verify_identity_token(
            identity_token=token,
            user_identifier="apple-user-1",
        )

    assert exc_info.value.message == "Apple identity token has expired"
