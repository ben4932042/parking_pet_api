from datetime import datetime

from pydantic import BaseModel, Field

from domain.entities.search_history import SearchHistoryPreference
from domain.entities.search_feedback import SearchResponseType


class UserSearchHistoryItemResponse(BaseModel):
    id: str
    query: str
    response_type: SearchResponseType
    preferences: list[SearchHistoryPreference] = Field(default_factory=list)
    result_ids: list[str] = Field(default_factory=list)
    result_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
