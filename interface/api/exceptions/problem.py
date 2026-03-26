from typing import Any, Optional

from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    title: str = Field(..., exclude=False, description="Human-readable title")
    status: int = Field(..., exclude=False, description="HTTP status")
    code: Optional[str] = Field(
        default=None, exclude=False, description="Stable machine readable error code"
    )
    detail: Optional[str] = Field(
        default=None, exclude=False, description="Error message"
    )
    instance: Optional[str] = Field(
        default=None,
        description="Request instance (can contain request_id)",
        exclude=True,
    )
    fields: Optional[dict[str, Any]] = Field(
        default=None, exclude=False, description="Field errors or additional data"
    )
