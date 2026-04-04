import pytest

from application.apple_auth import AppleAuthService
from application.exceptions import AuthenticationError, ValidationDomainError
from infrastructure.apple.auth import AppleIdentity


class UserRepoStub:
    def __init__(self, existing_user=None, created_user=None):
        self.existing_user = existing_user
        self.created_user = created_user
        self.calls = []

    async def get_user_by_apple_user_identifier(self, apple_user_identifier: str):
        self.calls.append(
            {
                "fn": "get_user_by_apple_user_identifier",
                "apple_user_identifier": apple_user_identifier,
            }
        )
        return self.existing_user

    async def register_apple_user(
        self,
        *,
        apple_user_identifier: str,
        name: str,
        pet_name: str | None = None,
        email: str | None = None,
    ):
        self.calls.append(
            {
                "fn": "register_apple_user",
                "apple_user_identifier": apple_user_identifier,
                "name": name,
                "pet_name": pet_name,
                "email": email,
            }
        )
        return self.created_user

    async def restore_user(self, user_id: str):
        self.calls.append({"fn": "restore_user", "user_id": user_id})
        if self.existing_user is None:
            return None
        return self.existing_user.model_copy(
            update={"is_deleted": False, "deleted_at": None}
        )


class AppleVerifierStub:
    def __init__(self, identity=None, error=None):
        self.identity = identity
        self.error = error
        self.calls = []

    async def verify_identity_token(
        self,
        *,
        identity_token: str,
        user_identifier: str,
    ):
        self.calls.append(
            {
                "identity_token": identity_token,
                "user_identifier": user_identifier,
            }
        )
        if self.error is not None:
            raise self.error
        return self.identity


@pytest.mark.asyncio
async def test_authenticate_returns_existing_apple_user(user_entity_factory):
    existing_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        source="apple",
        apple_user_identifier="apple-sub-1",
    )
    repo = UserRepoStub(existing_user=existing_user)
    verifier = AppleVerifierStub(identity=AppleIdentity(subject="apple-sub-1"))
    service = AppleAuthService(repo=repo, verifier=verifier)

    result = await service.authenticate(
        identity_token="token",
        authorization_code="code",
        user_identifier="apple-user-1",
        email=None,
        name="Ben",
        pet_name="Mochi",
    )

    assert result == existing_user
    assert repo.calls == [
        {
            "fn": "get_user_by_apple_user_identifier",
            "apple_user_identifier": "apple-sub-1",
        }
    ]


@pytest.mark.asyncio
async def test_authenticate_restores_deleted_apple_user(user_entity_factory):
    deleted_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        source="apple",
        apple_user_identifier="apple-sub-1",
    ).model_copy(update={"is_deleted": True})
    repo = UserRepoStub(existing_user=deleted_user)
    verifier = AppleVerifierStub(identity=AppleIdentity(subject="apple-sub-1"))
    service = AppleAuthService(repo=repo, verifier=verifier)

    result = await service.authenticate(
        identity_token="token",
        authorization_code="code",
        user_identifier="apple-user-1",
        email=None,
        name="Ben",
        pet_name="Mochi",
    )

    assert result.is_deleted is False
    assert repo.calls == [
        {
            "fn": "get_user_by_apple_user_identifier",
            "apple_user_identifier": "apple-sub-1",
        },
        {"fn": "restore_user", "user_id": "u1"},
    ]


@pytest.mark.asyncio
async def test_authenticate_creates_user_when_verified_payload_is_sufficient(
    user_entity_factory,
):
    created_user = user_entity_factory(
        identifier="u2",
        name="Ben",
        pet_name="Mochi",
        source="apple",
        apple_user_identifier="apple-sub-2",
    )
    repo = UserRepoStub(created_user=created_user)
    verifier = AppleVerifierStub(
        identity=AppleIdentity(subject="apple-sub-2", email="ben@example.com")
    )
    service = AppleAuthService(repo=repo, verifier=verifier)

    result = await service.authenticate(
        identity_token="token",
        authorization_code="code",
        user_identifier="apple-user-2",
        email=None,
        name="Ben",
        pet_name="Mochi",
    )

    assert result == created_user
    assert repo.calls == [
        {
            "fn": "get_user_by_apple_user_identifier",
            "apple_user_identifier": "apple-sub-2",
        },
        {
            "fn": "get_user_by_apple_user_identifier",
            "apple_user_identifier": "apple-user-2",
        },
        {
            "fn": "register_apple_user",
            "apple_user_identifier": "apple-sub-2",
            "name": "Ben",
            "pet_name": "Mochi",
            "email": "ben@example.com",
        },
    ]


@pytest.mark.asyncio
async def test_authenticate_requires_name_for_new_user():
    repo = UserRepoStub()
    verifier = AppleVerifierStub(identity=AppleIdentity(subject="apple-sub-3"))
    service = AppleAuthService(repo=repo, verifier=verifier)

    with pytest.raises(ValidationDomainError) as exc_info:
        await service.authenticate(
            identity_token="token",
            authorization_code="code",
            user_identifier="apple-user-3",
            email=None,
            name=None,
            pet_name=None,
        )

    assert exc_info.value.message == "Name is required to create an Apple user"


@pytest.mark.asyncio
async def test_authenticate_rejects_blank_authorization_code():
    repo = UserRepoStub()
    verifier = AppleVerifierStub(identity=AppleIdentity(subject="apple-sub-4"))
    service = AppleAuthService(repo=repo, verifier=verifier)

    with pytest.raises(AuthenticationError) as exc_info:
        await service.authenticate(
            identity_token="token",
            authorization_code="   ",
            user_identifier="apple-user-4",
            email=None,
            name="Ben",
            pet_name=None,
        )

    assert exc_info.value.message == "Apple authorization code is required"
