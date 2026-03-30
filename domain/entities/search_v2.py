from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from domain.entities.property_category import PropertyCategoryKey
from domain.entities.property import PropertyFilterCondition


class SearchRouteDecision(BaseModel):
    route: Literal["keyword", "semantic"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = Field(default="")


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


class SearchPlanV2(BaseModel):
    route: Literal["keyword", "semantic"]
    route_reason: str = Field(default="")
    route_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    filter_condition: PropertyFilterCondition = Field(
        default_factory=PropertyFilterCondition
    )
    semantic_extraction: Dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    used_fallback: bool = False
    fallback_reason: Optional[str] = None
