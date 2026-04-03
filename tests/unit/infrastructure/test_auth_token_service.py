import json
from datetime import UTC, datetime, timedelta

import pytest

from application.exceptions import AuthenticationError
from infrastructure.auth.tokens import AuthTokenService


def test_issue_and_verify_round_trip():
    service = AuthTokenService(
        signing_key="test-signing-key",
        ttl_seconds=3600,
        issuer="test-suite",
    )

    token = service.issue_access_token(user_id="u1", source="apple", session_version=2)
    claims = service.verify_access_token(token)

    assert claims.user_id == "u1"
    assert claims.source == "apple"
    assert claims.token_type == "access"
    assert claims.session_version == 2


def test_verify_rejects_tampered_signature():
    service = AuthTokenService(
        signing_key="test-signing-key",
        ttl_seconds=3600,
        issuer="test-suite",
    )
    token = service.issue_access_token(user_id="u1", source="apple", session_version=1)
    encoded_payload, _ = token.split(".")

    tampered_token = f"{encoded_payload}.tampered"

    with pytest.raises(AuthenticationError) as exc_info:
        service.verify_access_token(tampered_token)

    assert exc_info.value.message == "Invalid access token signature"


def test_verify_rejects_expired_token():
    service = AuthTokenService(
        signing_key="test-signing-key",
        ttl_seconds=3600,
        issuer="test-suite",
    )
    expired_payload = {
        "sub": "u1",
        "source": "apple",
        "type": "access",
        "sv": 1,
        "iss": "test-suite",
        "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
    }
    encoded_payload = service._b64url_encode(
        json.dumps(expired_payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
    )
    token = f"{encoded_payload}.{service._sign(encoded_payload)}"

    with pytest.raises(AuthenticationError) as exc_info:
        service.verify_access_token(token)

    assert exc_info.value.message == "Access token has expired"
