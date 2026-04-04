from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from domain.entities.property_category import PropertyCategoryKey


DEFAULT_SEARCH_RADIUS_METERS = 10000


class PropertyFilterCondition(BaseModel):
    mongo_query: dict = Field(default_factory=dict)
    matched_fields: list[str] = Field(default_factory=list)
    preferences: list[dict] = Field(default_factory=list)
    min_rating: float = Field(default=0.0)
    landmark_context: str | None = Field(default=None)
    travel_time_limit_min: int | None = Field(default=None)
    open_window_start_minutes: int | None = Field(default=None)
    open_window_end_minutes: int | None = Field(default=None)
    search_radius_meters: int = Field(default=DEFAULT_SEARCH_RADIUS_METERS)
    explanation: str = Field(default="")


SearchExecutionMode = Literal["keyword", "semantic"]


class SearchRouteDecision(BaseModel):
    execution_modes: list[SearchExecutionMode] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_route(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "execution_modes" not in value
            and "route" in value
        ):
            route = value.get("route")
            if route:
                value = {**value, "execution_modes": [route]}
        return value

    @model_validator(mode="after")
    def _normalize_execution_modes(self):
        self.execution_modes = list(dict.fromkeys(self.execution_modes))
        if not self.execution_modes:
            raise ValueError("execution_modes cannot be empty.")
        return self

    @property
    def route(self) -> SearchExecutionMode:
        return self.execution_modes[0]


class TypoCorrectionIntent(BaseModel):
    corrected_query: Optional[str] = None
    changed: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class LocationIntent(BaseModel):
    kind: Literal["landmark", "address", "none"] = "none"
    value: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class CategoryIntent(BaseModel):
    category_key: Optional[PropertyCategoryKey] = None
    primary_type: Optional[str] = None
    matched_from: Literal["primary_type", "category", "none"] = "none"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class PetFeatureIntent(BaseModel):
    features: Dict[str, bool] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class QualityIntent(BaseModel):
    min_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    is_open: Optional[bool] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class TimeIntent(BaseModel):
    open_window_start_minutes: Optional[int] = Field(default=None, ge=0, le=10079)
    open_window_end_minutes: Optional[int] = Field(default=None, ge=0, le=10079)
    label: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class DistanceIntent(BaseModel):
    transport_mode: Literal["driving", "bicycling", "walking"] = "driving"
    travel_time_limit_min: Optional[int] = Field(default=None, ge=0)
    search_radius_meters: Optional[int] = Field(default=None, ge=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = Field(default="")


class SearchPlan(BaseModel):
    execution_modes: list[SearchExecutionMode] = Field(default_factory=list)
    route_reason: str = Field(default="")
    route_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    filter_condition: PropertyFilterCondition = Field(
        default_factory=PropertyFilterCondition
    )
    semantic_extraction: Dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    used_fallback: bool = False
    fallback_reason: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_route(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "execution_modes" not in value
            and "route" in value
        ):
            route = value.get("route")
            if route:
                value = {**value, "execution_modes": [route]}
        return value

    @model_validator(mode="after")
    def _normalize_execution_modes(self):
        self.execution_modes = list(dict.fromkeys(self.execution_modes))
        if not self.execution_modes:
            raise ValueError("execution_modes cannot be empty.")
        return self

    @property
    def route(self) -> SearchExecutionMode:
        return self.execution_modes[0]
