from domain.entities.property_note import PropertyNoteEntity
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_note import IPropertyNoteRepository
from interface.api.exceptions.error import NotFoundError, ValidationDomainError


class PropertyNoteService:
    def __init__(
        self,
        note_repo: IPropertyNoteRepository,
        property_repo: IPropertyRepository,
    ):
        self.note_repo = note_repo
        self.property_repo = property_repo

    async def get_note(
        self, user_id: str, property_id: str
    ) -> PropertyNoteEntity | None:
        await self._ensure_property_exists(property_id)
        return await self.note_repo.get_by_user_and_property(user_id, property_id)

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
        return await self.note_repo.upsert(
            user_id=user_id,
            property_id=property_id,
            content=normalized_content,
        )

    async def delete_note(self, user_id: str, property_id: str) -> bool:
        await self._ensure_property_exists(property_id)
        return await self.note_repo.delete(user_id, property_id)

    async def list_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ) -> tuple[list[PropertyNoteEntity], int]:
        return await self.note_repo.list_by_user(
            user_id=user_id, page=page, size=size, query=query
        )

    async def _ensure_property_exists(self, property_id: str) -> None:
        existing = await self.property_repo.get_property_by_id(property_id)
        if existing is None:
            raise NotFoundError("Property not found")
