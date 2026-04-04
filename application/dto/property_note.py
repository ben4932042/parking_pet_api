from datetime import datetime

from pydantic import BaseModel

from application.dto.property import PropertyOverviewDto


class UserPropertyNoteListItemDto(BaseModel):
    property_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    property: PropertyOverviewDto | None = None


class UserPropertyNoteListPageDto(BaseModel):
    items: list[UserPropertyNoteListItemDto]
    total: int
    page: int
    size: int
    pages: int
