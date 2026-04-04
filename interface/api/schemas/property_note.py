from datetime import datetime

from pydantic import BaseModel, Field

from application.dto.property_note import UserPropertyNoteListItemDto


class PropertyNoteUpsertRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class PropertyNoteResponse(BaseModel):
    property_id: str
    content: str
    created_at: datetime
    updated_at: datetime


class UserPropertyNoteListItemResponse(UserPropertyNoteListItemDto):
    model_config = {"from_attributes": True}
