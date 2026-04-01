from typing import Literal

from pydantic import BaseModel, Field, field_validator

from domain.entities.search_feedback import SearchFeedbackPreference


class SearchFeedbackCreateRequest(BaseModel):
    query: str = Field(min_length=1)
    response_type: Literal[
        "semantic_search",
        "keyword_search",
        "hybrid_search",
        "fallback_search",
    ]
    reason: str = ""
    preferences: list[SearchFeedbackPreference] = Field(default_factory=list)
    result_ids: list[str] = Field(default_factory=list)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Query cannot be empty.")
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip()

    @field_validator("result_ids")
    @classmethod
    def normalize_result_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class SearchFeedbackCreateResponse(BaseModel):
    status: Literal["ok"] = "ok"
    feedback_id: str
