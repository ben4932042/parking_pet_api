from application.exceptions import NotFoundError, ValidationDomainError
from application.dto.property import PropertyOverviewDto
from application.dto.property_note import (
    UserPropertyNoteListItemDto,
    UserPropertyNoteListPageDto,
)
from domain.entities.property_note import PropertyNoteEntity
from domain.repositories.property import IPropertyRepository
from domain.repositories.user import IUserRepository
from domain.entities.user import UserEntity


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

    async def list_user_note_overviews(
        self,
        *,
        current_user: UserEntity,
        notes: list[PropertyNoteEntity],
        total: int,
        page: int,
        size: int,
        property_overviews: list[PropertyOverviewDto],
    ) -> UserPropertyNoteListPageDto:
        property_map = {
            property_item.id: property_item for property_item in property_overviews
        }
        favorite_property_ids = set(current_user.favorite_property_ids)
        items = [
            UserPropertyNoteListItemDto(
                property_id=note.property_id,
                content=note.content,
                created_at=note.created_at,
                updated_at=note.updated_at,
                property=property_map.get(note.property_id),
            )
            for note in notes
        ]
        items.sort(key=lambda item: item.property_id not in favorite_property_ids)
        pages = (total + size - 1) // size if size else 0
        return UserPropertyNoteListPageDto(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def _ensure_property_exists(self, property_id: str) -> None:
        existing = await self.property_repo.get_property_by_id(property_id)
        if existing is None:
            raise NotFoundError("Property not found")
