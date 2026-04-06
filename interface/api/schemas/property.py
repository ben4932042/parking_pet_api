from pydantic import BaseModel, Field

from application.dto.property import (
    PropertyAliasesDto,
    PropertyAuditLogDto,
    PropertyDetailDto,
    PropertyMutationDto,
    PropertyOverviewDto,
    PropertyPetFeaturesDto,
    PropertySearchResultDto,
)
from domain.entities.property_category import PropertyCategoryKey


class PropertyNearbyRequest(BaseModel):
    lat: float = Field(ge=-90, le=90, description="User or map center latitude.")
    lng: float = Field(ge=-180, le=180, description="User or map center longitude.")
    radius: int = Field(default=10000, description="Radius in meters")
    category: PropertyCategoryKey | None = Field(
        default=None,
        description=(
            "Frontend category filter. "
            "The backend expands this enum into one or more Google primary_type values. "
            "Example: restaurant includes restaurant, brunch_restaurant, bar, hot_pot_restaurant, and other restaurant subtypes."
        ),
    )
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=10000)


class PetRulesPatchRequest(BaseModel):
    leash_required: bool | None = None
    stroller_required: bool | None = None
    allow_on_floor: bool | None = None


class PetEnvironmentPatchRequest(BaseModel):
    stairs: bool | None = None
    outdoor_seating: bool | None = None
    spacious: bool | None = None
    indoor_ac: bool | None = None
    off_leash_possible: bool | None = None
    pet_friendly_floor: bool | None = None
    has_shop_pet: bool | None = None


class PetServicePatchRequest(BaseModel):
    pet_menu: bool | None = None
    free_water: bool | None = None
    free_treats: bool | None = None
    pet_seating: bool | None = None


class PropertyPetFeaturesPatchRequest(BaseModel):
    pet_rules: PetRulesPatchRequest | None = None
    pet_environment: PetEnvironmentPatchRequest | None = None
    pet_service: PetServicePatchRequest | None = None
    reason: str | None = None


class PropertyAliasesPatchRequest(BaseModel):
    manual_aliases: list[str] = Field(default_factory=list)
    reason: str | None = None


class PropertyOverviewResponse(PropertyOverviewDto):
    model_config = {"from_attributes": True}


class PropertySearchResponse(PropertySearchResultDto):
    model_config = {"from_attributes": True}


class PropertyDetailResponse(PropertyDetailDto):
    model_config = {"from_attributes": True}


class PropertyPetFeaturesResponse(PropertyPetFeaturesDto):
    model_config = {"from_attributes": True}


class PropertyAliasesResponse(PropertyAliasesDto):
    model_config = {"from_attributes": True}


class PropertyMutationResponse(PropertyMutationDto):
    model_config = {"from_attributes": True}


class PropertyCreateResponse(BaseModel):
    property_id: str


class PropertyAuditLogResponse(PropertyAuditLogDto):
    model_config = {"from_attributes": True}
