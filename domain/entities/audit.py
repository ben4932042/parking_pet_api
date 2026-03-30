from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from domain.entities import PyObjectId

SourceType = Literal["user", "admin", "system", "api", "job"]


class ActorInfo(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    source: SourceType = "api"


class PropertyAuditAction(StrEnum):
    CREATE = "create"
    SYNC = "sync"
    PET_FEATURES_OVERRIDE = "pet_features_override"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"


class PropertyAuditLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    property_id: str
    action: PropertyAuditAction
    actor: ActorInfo
    reason: Optional[str] = None
    source: str = "api"
    request_id: Optional[str] = None
    changes: dict[str, dict[str, Any]] = Field(default_factory=dict)
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
