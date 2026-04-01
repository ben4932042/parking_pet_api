from datetime import datetime

from pydantic import BaseModel


class UserSearchHistoryItemResponse(BaseModel):
    query: str
    searched_at: datetime

    model_config = {"from_attributes": True}
