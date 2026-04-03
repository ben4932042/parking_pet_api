import pytest

from application.auth_session import AuthSessionService
from application.exceptions import AuthenticationError


class UserRepoStub:
    def __init__(self, *, user=None, rotated_user=None, revoked_user=None):
        self.user = user
        self.rotated_user = rotated_user if rotated_user is not None else user
        self.revoked_user = revoked_user if revoked_user is not None else user
        self.calls = []

    async def get_user_by_id(self, user_id: str):
        self.calls.append({"fn": "get_user_by_id", "user_id": user_id})
        return self.user

    async def start_auth_session(self, *, user_id: str, refresh_token_hash: str):
        self.calls.append(
            {
                "fn": "start_auth_session",
                "user_id": user_id,
                "refresh_token_hash": refresh_token_hash,
            }
        )
        return self.user

    async def rotate_refresh_token(self, *, user_id: str, refresh_token_hash: str):
        self.calls.append(
            {
                "fn": "rotate_refresh_token",
                "user_id": user_id,
                "refresh_token_hash": refresh_token_hash,
            }
        )
        return self.rotated_user

    async def revoke_auth_session(self, *, user_id: str):
        self.calls.append({"fn": "revoke_auth_session", "user_id": user_id})
        return self.revoked_user


class TokenServiceStub:
    def __init__(self, *, access_token: str = "access-1", refresh_token: str = "refresh-1"):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.claims = None
        self.calls = []

    def issue_access_token(self, *, user_id: str, source: str, session_version: int) -> str:
        self.calls.append(
            {
                "fn": "issue_access_token",
                "user_id": user_id,
                "source": source,
                "session_version": session_version,
            }
        )
        return self.access_token

    def issue_refresh_token(self, *, user_id: str, source: str, session_version: int) -> str:
        self.calls.append(
            {
                "fn": "issue_refresh_token",
                "user_id": user_id,
                "source": source,
                "session_version": session_version,
            }
        )
        return self.refresh_token

    def verify_access_token(self, token: str):
        raise AssertionError("verify_access_token should not be called in this test")

    def verify_refresh_token(self, token: str):
        self.calls.append({"fn": "verify_refresh_token", "token": token})
        if self.claims is None:
            raise AssertionError("claims must be set for refresh verification")
        return self.claims


class ClaimsStub:
    def __init__(self, *, user_id: str, source: str, session_version: int):
        self.user_id = user_id
        self.source = source
        self.session_version = session_version
        self.token_type = "refresh"


@pytest.mark.asyncio
async def test_start_session_issues_tokens_for_incremented_session_version(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben", source="basic")
    session_user = user.model_copy(update={"session_version": 1})
    repo = UserRepoStub(user=session_user)
    access_service = TokenServiceStub(access_token="access-1")
    refresh_service = TokenServiceStub(refresh_token="refresh-1")
    service = AuthSessionService(
        repo=repo,
        access_token_service=access_service,
        refresh_token_service=refresh_service,
    )

    session = await service.start_session(user=user)

    assert session.access_token == "access-1"
    assert session.refresh_token == "refresh-1"
    assert session.user.session_version == 1
    assert repo.calls[0]["fn"] == "start_auth_session"
    assert access_service.calls == [
        {
            "fn": "issue_access_token",
            "user_id": "u1",
            "source": "basic",
            "session_version": 1,
        }
    ]


@pytest.mark.asyncio
async def test_refresh_session_rotates_refresh_token(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben", source="apple").model_copy(
        update={
            "session_version": 1,
            "refresh_token_hash": AuthSessionService._hash_token("refresh-old"),
        }
    )
    refreshed_user = user.model_copy(
        update={"refresh_token_hash": AuthSessionService._hash_token("refresh-new")}
    )
    repo = UserRepoStub(user=user, rotated_user=refreshed_user)
    access_service = TokenServiceStub(access_token="access-new")
    refresh_service = TokenServiceStub(refresh_token="refresh-new")
    refresh_service.claims = ClaimsStub(
        user_id="u1",
        source="apple",
        session_version=1,
    )
    service = AuthSessionService(
        repo=repo,
        access_token_service=access_service,
        refresh_token_service=refresh_service,
    )
    session = await service.refresh_session(refresh_token="refresh-old")

    assert session.access_token == "access-new"
    assert session.refresh_token == "refresh-new"
    assert repo.calls == [
        {"fn": "get_user_by_id", "user_id": "u1"},
        {
            "fn": "rotate_refresh_token",
            "user_id": "u1",
            "refresh_token_hash": AuthSessionService._hash_token("refresh-new"),
        },
    ]


@pytest.mark.asyncio
async def test_refresh_session_rejects_mismatched_refresh_token_hash(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben", source="apple").model_copy(
        update={"session_version": 1, "refresh_token_hash": "other-hash"}
    )
    repo = UserRepoStub(user=user)
    access_service = TokenServiceStub()
    refresh_service = TokenServiceStub(refresh_token="refresh-new")
    refresh_service.claims = ClaimsStub(
        user_id="u1",
        source="apple",
        session_version=1,
    )
    service = AuthSessionService(
        repo=repo,
        access_token_service=access_service,
        refresh_token_service=refresh_service,
    )

    with pytest.raises(AuthenticationError) as exc_info:
        await service.refresh_session(refresh_token="refresh-old")

    assert exc_info.value.message == "Invalid authentication credentials"


@pytest.mark.asyncio
async def test_logout_revokes_auth_session(user_entity_factory):
    user = user_entity_factory(identifier="u1", name="Ben", source="basic")
    repo = UserRepoStub(user=user)
    service = AuthSessionService(
        repo=repo,
        access_token_service=TokenServiceStub(),
        refresh_token_service=TokenServiceStub(),
    )

    await service.logout(user_id="u1")

    assert repo.calls == [{"fn": "revoke_auth_session", "user_id": "u1"}]
