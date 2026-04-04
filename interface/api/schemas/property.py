from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from domain.entities.audit import ActorInfo, PropertyAuditAction
from domain.entities.enrichment import AIAnalysis
from domain.entities.property_category import PropertyCategoryKey
from domain.entities.property import (
    OpeningPeriod,
    PetEnvironmentOverride,
    PetFeatures,
    PetFeaturesOverride,
    PropertyManualOverrides,
    PetRulesOverride,
    PetServiceOverride,
)


class PreferenceTag(BaseModel):
    key: str
    label: str


class PropertyKeywordRequest(BaseModel):
    q: str
    type: Optional[str] = Field(default=None)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PropertyNearbyRequest(BaseModel):
    lat: float = Field(ge=-90, le=90, description="User or map center latitude.")
    lng: float = Field(ge=-180, le=180, description="User or map center longitude.")
    radius: int = Field(default=10000, description="Radius in meters")
    category: Optional[PropertyCategoryKey] = Field(
        default=None,
        description=(
            "Frontend category filter. "
            "The backend expands this enum into one or more Google primary_type values. "
            "Example: restaurant includes restaurant, brunch_restaurant, bar, hot_pot_restaurant, and other restaurant subtypes."
        ),
    )
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PropertyOverviewResponse(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    category: Optional[str]
    types: List[str]
    rating: float
    is_open: Optional[bool]
    has_note: bool = False
    is_favorite: bool = False

    model_config = {"from_attributes": True}


class PropertySearchResponse(BaseModel):
    status: str
    user_query: str
    response_type: str
    preferences: List[PreferenceTag] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    results: List[PropertyOverviewResponse] = Field(default_factory=list)


class PropertyDetailSchema(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    types: List[str]
    rating: float
    tags: List[str]
    regular_opening_hours: Optional[List[OpeningPeriod]]
    ai_analysis: AIAnalysis
    manual_overrides: Optional[PropertyManualOverrides] = None
    effective_pet_features: Optional[PetFeatures] = None
    created_by: Optional[ActorInfo] = None
    updated_by: Optional[ActorInfo] = None
    created_at: datetime
    updated_at: datetime
    deleted_by: Optional[ActorInfo] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False


class PropertyDetailResponse(PropertyDetailSchema):
    model_config = {"from_attributes": True}


class PropertyPetFeaturesPatchRequest(BaseModel):
    pet_rules: Optional[PetRulesOverride] = None
    pet_environment: Optional[PetEnvironmentOverride] = None
    pet_service: Optional[PetServiceOverride] = None
    reason: Optional[str] = None


class PropertyAliasesPatchRequest(BaseModel):
    manual_aliases: List[str] = Field(default_factory=list)
    reason: Optional[str] = None


class PropertyPetFeaturesResponse(BaseModel):
    property_id: str
    inferred_pet_features: PetFeatures
    manual_pet_features: Optional[PetFeaturesOverride] = None
    effective_pet_features: PetFeatures
    updated_by: Optional[ActorInfo] = None
    updated_at: Optional[datetime] = None
    reason: Optional[str] = None


class PropertyAliasesResponse(BaseModel):
    property_id: str
    aliases: List[str] = Field(default_factory=list)
    manual_aliases: List[str] = Field(default_factory=list)
    updated_by: Optional[ActorInfo] = None
    updated_at: Optional[datetime] = None
    reason: Optional[str] = None


class PropertyMutationResponse(BaseModel):
    property_id: str
    status: str
    is_deleted: bool
    updated_by: Optional[ActorInfo] = None
    updated_at: Optional[datetime] = None
    deleted_by: Optional[ActorInfo] = None
    deleted_at: Optional[datetime] = None


class PropertyCreateResponse(BaseModel):
    property_id: str


class PropertyAuditLogResponse(BaseModel):
    property_id: str
    action: PropertyAuditAction
    actor: ActorInfo
    reason: Optional[str] = None
    source: str
    changes: dict
    before: Optional[dict] = None
    after: Optional[dict] = None
    created_at: datetime
