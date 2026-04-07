from abc import ABC, abstractmethod

from application.exceptions import (
    AuthenticationError,
    ConflictError,
    ValidationDomainError,
)
from domain.entities.user import UserEntity
from domain.repositories.user import IUserRepository


class VerifiedAppleIdentity(ABC):
    @property
    @abstractmethod
    def subject(self) -> str: ...

    @property
    @abstractmethod
    def email(self) -> str | None: ...


class IAppleIdentityVerifier(ABC):
    @abstractmethod
    async def verify_identity_token(
        self,
        *,
        identity_token: str,
        user_identifier: str,
    ) -> VerifiedAppleIdentity: ...


class AppleAuthService:
    def __init__(
        self,
        repo: IUserRepository,
        verifier: IAppleIdentityVerifier,
    ) -> None:
        self.repo = repo
        self.verifier = verifier

    async def authenticate(
        self,
        *,
        identity_token: str,
        authorization_code: str,
        user_identifier: str,
        email: str | None = None,
        name: str | None = None,
        pet_name: str | None = None,
    ) -> UserEntity:
        if not authorization_code.strip():
            raise AuthenticationError("Apple authorization code is required")

        verified_identity = await self.verifier.verify_identity_token(
            identity_token=identity_token,
            user_identifier=user_identifier,
        )
        existing_user = await self.repo.get_user_by_apple_user_identifier(
            verified_identity.subject
        )
        if existing_user is None and verified_identity.subject != user_identifier:
            existing_user = await self.repo.get_user_by_apple_user_identifier(
                user_identifier
            )
        if existing_user is not None:
            if existing_user.is_deleted:
                restored_user = await self.repo.restore_user(existing_user.id)
                if restored_user is not None:
                    return restored_user
            return existing_user

        display_name = self._require_display_name(name=name)
        return await self.repo.register_apple_user(
            apple_user_identifier=verified_identity.subject,
            name=display_name,
            pet_name=pet_name,
            email=email or verified_identity.email,
        )

    async def link_guest_user(
        self,
        *,
        current_user: UserEntity,
        identity_token: str,
        authorization_code: str,
        user_identifier: str,
        email: str | None = None,
    ) -> UserEntity:
        if current_user.source != "guest":
            raise ValidationDomainError("Only guest users can link an Apple account")
        if not authorization_code.strip():
            raise AuthenticationError("Apple authorization code is required")

        verified_identity = await self.verifier.verify_identity_token(
            identity_token=identity_token,
            user_identifier=user_identifier,
        )
        existing_user = await self.repo.get_user_by_apple_user_identifier(
            verified_identity.subject
        )
        if existing_user is None and verified_identity.subject != user_identifier:
            existing_user = await self.repo.get_user_by_apple_user_identifier(
                user_identifier
            )
        if existing_user is not None and str(existing_user.id) != str(current_user.id):
            raise ConflictError("Apple account is already linked to another user")

        linked_user = await self.repo.link_guest_user_to_apple(
            user_id=str(current_user.id),
            apple_user_identifier=verified_identity.subject,
            email=email or verified_identity.email,
        )
        if linked_user is None:
            raise AuthenticationError("Invalid authentication credentials")
        return linked_user

    @staticmethod
    def _require_display_name(*, name: str | None) -> str:
        if name is not None and name.strip():
            return name.strip()
        raise ValidationDomainError("Name is required to create an Apple user")
