from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from interface.api.schemas.property import PropertyOverviewResponse


class PropertyNoteUpsertRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class PropertyNoteResponse(BaseModel):
    property_id: str
    content: str
    created_at: datetime
    updated_at: datetime


class UserPropertyNoteListItemResponse(BaseModel):
    property_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    property: Optional[PropertyOverviewResponse] = None
