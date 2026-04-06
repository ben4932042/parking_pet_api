from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ActorDto(BaseModel):
    user_id: str | None = None
    name: str
    role: str
    source: str


class TimePointDto(BaseModel):
    day: int
    hour: int
    minute: int


class OpeningPeriodDto(BaseModel):
    open: TimePointDto
    close: TimePointDto | None = None


class ReviewDto(BaseModel):
    author: str | None = None
    rating: float | None = None
    text: str | None = None
    time: str | None = None


class PetRulesDto(BaseModel):
    leash_required: bool
    stroller_required: bool
    allow_on_floor: bool


class PetEnvironmentDto(BaseModel):
    stairs: bool
    outdoor_seating: bool
    spacious: bool
    indoor_ac: bool
    off_leash_possible: bool
    pet_friendly_floor: bool
    has_shop_pet: bool


class PetServiceDto(BaseModel):
    pet_menu: bool
    free_water: bool
    free_treats: bool
    pet_seating: bool


class PetFeaturesDto(BaseModel):
    rules: PetRulesDto
    environment: PetEnvironmentDto
    services: PetServiceDto


class PetRulesOverrideDto(BaseModel):
    leash_required: bool | None = None
    stroller_required: bool | None = None
    allow_on_floor: bool | None = None


class PetEnvironmentOverrideDto(BaseModel):
    stairs: bool | None = None
    outdoor_seating: bool | None = None
    spacious: bool | None = None
    indoor_ac: bool | None = None
    off_leash_possible: bool | None = None
    pet_friendly_floor: bool | None = None
    has_shop_pet: bool | None = None


class PetServiceOverrideDto(BaseModel):
    pet_menu: bool | None = None
    free_water: bool | None = None
    free_treats: bool | None = None
    pet_seating: bool | None = None


class PetFeaturesOverrideDto(BaseModel):
    rules: PetRulesOverrideDto | None = None
    environment: PetEnvironmentOverrideDto | None = None
    services: PetServiceOverrideDto | None = None


class AIAnalysisDto(BaseModel):
    venue_type: str
    ai_summary: str
    pet_features: PetFeaturesDto
    highlights: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rating: float


class PropertyManualOverridesDto(BaseModel):
    pet_features: PetFeaturesOverrideDto | None = None
    updated_by: ActorDto | None = None
    updated_at: datetime | None = None
    reason: str | None = None


class PropertyOverviewDto(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    category: str | None = None
    types: list[str] = Field(default_factory=list)
    rating: float
    is_open: bool | None = None
    has_note: bool = False
    is_favorite: bool = False


class PropertyMapBboxDto(BaseModel):
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


class PropertyMapResultDto(BaseModel):
    bbox: PropertyMapBboxDto
    query: str | None = None
    category: str | None = None
    items: list[PropertyOverviewDto] = Field(default_factory=list)
    total_in_bbox: int
    returned_count: int
    truncated: bool
    suggest_clustering: bool


class PropertySearchResultDto(BaseModel):
    status: str
    user_query: str
    response_type: str
    preferences: list[dict[str, str]] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    results: list[PropertyOverviewDto] = Field(default_factory=list)


class PropertyDetailDto(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    manual_aliases: list[str] = Field(default_factory=list)
    address: str
    latitude: float
    longitude: float
    types: list[str] = Field(default_factory=list)
    rating: float
    tags: list[str] = Field(default_factory=list)
    regular_opening_hours: list[OpeningPeriodDto] | None = None
    ai_analysis: AIAnalysisDto
    manual_overrides: PropertyManualOverridesDto | None = None
    effective_pet_features: PetFeaturesDto | None = None
    created_by: ActorDto | None = None
    updated_by: ActorDto | None = None
    created_at: datetime
    updated_at: datetime
    deleted_by: ActorDto | None = None
    deleted_at: datetime | None = None
    is_deleted: bool = False


class PropertyPetFeaturesDto(BaseModel):
    property_id: str
    inferred_pet_features: PetFeaturesDto
    manual_pet_features: PetFeaturesOverrideDto | None = None
    effective_pet_features: PetFeaturesDto
    updated_by: ActorDto | None = None
    updated_at: datetime | None = None
    reason: str | None = None


class PropertyAliasesDto(BaseModel):
    property_id: str
    aliases: list[str] = Field(default_factory=list)
    manual_aliases: list[str] = Field(default_factory=list)
    updated_by: ActorDto | None = None
    updated_at: datetime | None = None
    reason: str | None = None


class PropertyMutationDto(BaseModel):
    property_id: str
    status: str
    is_deleted: bool
    updated_by: ActorDto | None = None
    updated_at: datetime | None = None
    deleted_by: ActorDto | None = None
    deleted_at: datetime | None = None


class PropertyCreateResultDto(BaseModel):
    property_id: str
    place_id: str
    outcome: str
    changed: bool
    existing_before: bool


class PropertyMutationResultDto(BaseModel):
    mutation: PropertyMutationDto
    place_id: str
    operation: str
    outcome: str
    changed: bool
    existing_before: bool
    reason: str | None = None
    mode: str | None = None


class PropertyAuditLogDto(BaseModel):
    property_id: str
    action: str
    actor: ActorDto
    reason: str | None = None
    source: str
    changes: dict[str, Any]
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    created_at: datetime
