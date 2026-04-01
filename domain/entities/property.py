from datetime import UTC, datetime, timedelta, timezone
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from domain.entities.audit import ActorInfo
from domain.entities.property_category import get_primary_category_key
from domain.entities.enrichment import (
    AIAnalysis,
    PetEnvironment,
    PetFeatures,
    PetRules,
    PetService,
)


class PointLocation(BaseModel):
    type: Literal["Point"] = Field(default="Point")
    coordinates: List[float] = Field(..., description="[lng, lat]")


class TimePoint(BaseModel):
    day: int = Field(..., ge=0, le=6, description="星期幾 (0=週日, 6=週六)")
    hour: int = Field(..., ge=0, le=23, description="24小時制的時")
    minute: int = Field(..., ge=0, le=59, description="分")

    def to_total_minutes(self) -> int:
        return self.day * 1440 + self.hour * 60 + self.minute


class OpeningPeriod(BaseModel):
    open: TimePoint
    close: Optional[TimePoint] = None

    def to_segments(self) -> list[dict]:
        if self.open and not self.close:
            if self.open.day == 0 and self.open.hour == 0 and self.open.minute == 0:
                return [{"s": 0, "e": 10079}]
            else:
                s = self.open.day * 1440 + self.open.hour * 60 + self.open.minute
                return [{"s": s, "e": s + 1439}]

        if self.open and self.close:
            s_time = self.open.day * 1440 + self.open.hour * 60 + self.open.minute
            e_time = self.close.day * 1440 + self.close.hour * 60 + self.close.minute
            if e_time <= s_time:
                e_time += 10080
            return [{"s": s_time, "e": e_time}]

        return []


class OpSegment(BaseModel):
    s: int = Field(description="開始分鐘數")
    e: int = Field(description="結束分鐘數")


class PetRulesOverride(BaseModel):
    leash_required: Optional[bool] = None
    stroller_required: Optional[bool] = None
    allow_on_floor: Optional[bool] = None


class PetEnvironmentOverride(BaseModel):
    stairs: Optional[bool] = None
    outdoor_seating: Optional[bool] = None
    spacious: Optional[bool] = None
    indoor_ac: Optional[bool] = None
    off_leash_possible: Optional[bool] = None
    pet_friendly_floor: Optional[bool] = None
    has_shop_pet: Optional[bool] = None


class PetServiceOverride(BaseModel):
    pet_menu: Optional[bool] = None
    free_water: Optional[bool] = None
    free_treats: Optional[bool] = None
    pet_seating: Optional[bool] = None


class PetFeaturesOverride(BaseModel):
    rules: Optional[PetRulesOverride] = None
    environment: Optional[PetEnvironmentOverride] = None
    services: Optional[PetServiceOverride] = None


class PropertyManualOverrides(BaseModel):
    pet_features: Optional[PetFeaturesOverride] = None
    updated_by: Optional[ActorInfo] = None
    updated_at: Optional[datetime] = None
    reason: Optional[str] = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_pet_features(
    inferred: PetFeatures,
    overrides: Optional[PetFeaturesOverride],
) -> PetFeatures:
    if overrides is None:
        return inferred

    override_payload = overrides.model_dump(exclude_none=True)
    if not override_payload:
        return inferred

    inferred_payload = inferred.model_dump()
    merged_payload = _deep_merge(inferred_payload, override_payload)
    return PetFeatures(
        rules=PetRules(**merged_payload["rules"]),
        environment=PetEnvironment(**merged_payload["environment"]),
        services=PetService(**merged_payload["services"]),
    )


class PropertyEntity(BaseModel):
    id: str = Field(alias="_id")
    name: str = Field(description="Name of the property")
    place_id: str = Field(description="Google Maps Place ID")
    aliases: List[str] = Field(default_factory=list)
    manual_aliases: List[str] = Field(default_factory=list)
    search_text: Optional[str] = None
    search_embedding: Optional[List[float]] = None
    embedding_version: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_updated_at: Optional[datetime] = None
    latitude: float = Field(description="Latitude of the property", ge=-90, le=90)
    longitude: float = Field(description="Longitude of the property", ge=-180, le=180)
    regular_opening_hours: Optional[List[OpeningPeriod]]

    address: str = Field(
        description="地址。僅用於『行政區名稱』（如：台北市、大安區、魚池鄉）或『路名』。"
        "禁止將具體地標（如：日月潭、101、台北車站）放進此欄位，具體地標請填入 landmark_context。"
        "地址。僅用於『行政區名稱』或『路名』。"
        "【嚴禁】在此搜尋『餐廳類型』或『食物關鍵字』（如：火鍋、咖啡、民宿）。"
        "這類關鍵字請統一轉換為 primary_type 篩選。"
    )
    ai_analysis: AIAnalysis
    manual_overrides: Optional[PropertyManualOverrides] = None
    effective_pet_features: Optional[PetFeatures] = None
    created_by: Optional[ActorInfo] = None
    updated_by: Optional[ActorInfo] = None
    deleted_by: Optional[ActorInfo] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # generated field
    op_segments: List[OpSegment] = Field(default_factory=list)
    location: Optional[PointLocation] = Field(
        default=None,
        description="地理座標欄位。注意：絕對禁止在 mongo_query 中自行生成 $near 或經緯度數字。",
    )
    primary_type: str = Field(
        description=(
            "地點的分類標籤。請根據使用者需求精準匹配下列關鍵字：\n"
            "- cafe: 包含咖啡廳、甜點店(dessert_shop)、下午茶、蛋糕(cake_shop)、麵包店(bakery)\n"
            "- hot_pot_restaurant: 火鍋店\n"
            "- yakiniku_restaurant: 燒肉、烤肉\n"
            "- ramen_restaurant: 拉麵\n"
            "- brunch_restaurant: 早午餐\n"
            "- bistro: 餐酒館\n"
            "- restaurant: 一般餐廳 (若上述皆不符合則用此項)\n"
            "- lodging: 民宿、旅館、住宿\n"
            "- veterinary_care: 醫院、獸醫、看病\n"
            "- pet_care: 寵物美容、洗澡、剪毛\n"
            "- pet_store: 寵物用品、買東西"
            "- park: 公園(park)、健行(hiking_area)、寵物公園(dog_park)、花園。\n"
            "- hospital: 獸醫院(veterinary_care)。\n"
            "- grooming: 寵物美容、寵物洗澡(pet_care)。\n"
            "- petSupplyStore: 寵物用品店(pet_store)。\n"
            "- lodging: 旅館、民宿、寵物住宿(pet_boarding_service)。"
        )
    )

    rating: Optional[float] = Field(
        default=0.0,
        description="店家的 AI 綜合評分 (0.0-5.0)。若提到『高品質』、『熱門』、『推薦』或『好店』，請使用 {'$gte': 4.0}。",
    )

    is_open: Optional[bool] = Field(
        default=None,
        description="即時營業狀態。若提到『現在有開嗎』、『營業中』、『不想白跑一趟』，請設為 true。",
    )

    category: Optional[str] = Field(default=None, description="前端產品分類名稱。")
    types: List[str] = Field(default_factory=list, description="primary_type 的別名。")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def generate_segments(self) -> "PropertyEntity":
        if not self.regular_opening_hours:
            return self
        try:
            new_segments = []
            for period in self.regular_opening_hours:
                raw_segments = period.to_segments()
                for seg in raw_segments:
                    new_segments.append(OpSegment(**seg))

            new_segments.sort(key=lambda x: x.s)
            self.op_segments = new_segments
            return self
        except Exception as e:
            print(f"Error generating op_segments: {e}")
            return self

    @model_validator(mode="after")
    def generate_location(self) -> "PropertyEntity":
        if not self.longitude or not self.latitude:
            return self

        self.location = PointLocation(coordinates=[self.longitude, self.latitude])
        return self

    @model_validator(mode="after")
    def generate_rating(self) -> "PropertyEntity":
        self.rating = self.ai_analysis.ai_rating
        return self

    @model_validator(mode="after")
    def generate_effective_pet_features(self) -> "PropertyEntity":
        self.effective_pet_features = merge_pet_features(
            self.ai_analysis.pet_features,
            self.manual_overrides.pet_features if self.manual_overrides else None,
        )
        return self

    @model_validator(mode="after")
    def is_currently_open(self) -> "PropertyEntity":
        if not self.op_segments:
            self.is_open = None
            return self

        tz_taiwan = timezone(timedelta(hours=8))
        now = datetime.now(tz_taiwan)

        day_of_week = (now.weekday() + 1) % 7
        current_minutes = (day_of_week * 1440) + (now.hour * 60) + now.minute

        for segment in self.op_segments:
            start = segment.s
            end = segment.e

            if start <= current_minutes <= end:
                self.is_open = True
                return self
        self.is_open = False
        return self

    @model_validator(mode="after")
    def is_open_now(self) -> "PropertyEntity":
        self.types = [self.primary_type] if self.primary_type else []
        self.category = get_primary_category_key(self.primary_type)
        return self


class PropertyDetailEntity(BaseModel):
    id: str
    name: str
    aliases: List[str] = Field(default_factory=list)
    manual_aliases: List[str] = Field(default_factory=list)
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_by: Optional[ActorInfo] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False


class PropertySearchResultEntity(BaseModel):
    status: str
    original_tags: List[dict] = Field(default_factory=list)
    active_tags: List[dict] = Field(default_factory=list)
    results: List[PropertyEntity] = Field(default_factory=list)


DEFAULT_SEARCH_RADIUS_METERS = 10000


class PropertyFilterCondition(BaseModel):
    mongo_query: dict = Field(default_factory=dict)
    matched_fields: List[str] = Field(default_factory=list)
    preferences: List[dict] = Field(default_factory=list)
    min_rating: float = Field(default=0.0)
    landmark_context: Optional[str] = Field(default=None)
    travel_time_limit_min: Optional[int] = Field(default=None)
    search_radius_meters: int = Field(default=DEFAULT_SEARCH_RADIUS_METERS)
    explanation: str = Field(default="")
