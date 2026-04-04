from application.exceptions import NotFoundError, ValidationDomainError
from domain.entities.property_note import PropertyNoteEntity
from domain.repositories.property import IPropertyRepository
from domain.repositories.user import IUserRepository


class PropertyNoteService:
    def __init__(
        self,
        user_repo: IUserRepository,
        property_repo: IPropertyRepository,
    ):
        self.user_repo = user_repo
        self.property_repo = property_repo

    async def get_note(
        self, user_id: str, property_id: str
    ) -> PropertyNoteEntity | None:
        await self._ensure_property_exists(property_id)
        return await self.user_repo.get_property_note(user_id, property_id)

    async def save_note(
        self, user_id: str, property_id: str, content: str
    ) -> PropertyNoteEntity:
        normalized_content = content.strip()
        if not normalized_content:
            raise ValidationDomainError("Note content cannot be empty.")
        if len(normalized_content) > 2000:
            raise ValidationDomainError(
                "Note content must be 2000 characters or fewer."
            )

        await self._ensure_property_exists(property_id)
        return await self.user_repo.upsert_property_note(
            user_id=user_id,
            property_id=property_id,
            content=normalized_content,
        )

    async def delete_note(self, user_id: str, property_id: str) -> bool:
        await self._ensure_property_exists(property_id)
        return await self.user_repo.delete_property_note(user_id, property_id)

    async def list_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ) -> tuple[list[PropertyNoteEntity], int]:
        return await self.user_repo.list_property_notes(
            user_id=user_id, page=page, size=size, query=query
        )

    async def _ensure_property_exists(self, property_id: str) -> None:
        existing = await self.property_repo.get_property_by_id(property_id)
        if existing is None:
            raise NotFoundError("Property not found")
