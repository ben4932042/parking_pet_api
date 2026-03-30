from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class PlaceCandidate(BaseModel):
    id: str
    origin_search_name: str
    display_name: str
    place_id: str
    latitude: float
    longitude: float
    address: str
    primary_type: Optional[str] = None
    types: List[str]
    business_status: Optional[str] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None
    user_rating_count: int
    payment_methods: Optional[Dict[str, bool]] = None
    parking_options: Optional[Dict[str, bool]] = None
    accessibility_options: Optional[Dict[str, bool]] = None
    takeout: Optional[bool] = None
    delivery: Optional[bool] = None
    dine_in: Optional[bool] = None


class Review(BaseModel):
    author: Optional[str]
    rating: Optional[float]
    text: Optional[str]
    time: Optional[str]


class PlaceDetail(BaseModel):
    id: str
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[str] = None
    regular_opening_hours: Optional[List[Dict]] = None
    allows_dogs: Optional[bool] = None
    outdoor_seating: Optional[bool] = None
    reservable: Optional[bool] = None
    good_for_children: Optional[bool] = None
    good_for_groups: Optional[bool] = None
    serves_beer: Optional[bool] = None
    serves_wine: Optional[bool] = None
    reviews: List[Review] = []


class AnalysisSource(PlaceCandidate, PlaceDetail):
    id: str = Field(alias="_id")
    model_config = {"populate_by_name": True, "from_attributes": True}

    @classmethod
    def from_parts(
        cls, basic: PlaceCandidate, insight: PlaceDetail
    ) -> "AnalysisSource":
        basic_dict = basic.model_dump()
        insight_dict = insight.model_dump() if insight else {}

        return cls(**{**basic_dict, **insight_dict})


class PetRules(BaseModel):
    leash_required: bool = Field(
        default=False,
        description="是否強制牽繩。若使用者要求『免牽繩』或『放手玩』，請搜尋 false；若提到『安全規範』則搜尋 true。",
    )
    stroller_required: bool = Field(
        default=False,
        description="是否需推車/提籠。當提到『沒推車』或『想直接進去』時，請搜尋 false。",
    )
    allow_on_floor: bool = Field(
        default=False,
        description="毛孩是否可落地。當提到『可以走動』、『不用坐車』、『狗狗落地』時，請設為 true。",
    )


class PetEnvironment(BaseModel):
    stairs: bool = Field(
        default=False,
        description="是否有階梯（影響推車便利性）。從評論或店名關鍵字判定",
    )
    outdoor_seating: bool = Field(
        default=False,
        description="是否有戶外座位。參考 Google 原始欄位或評論提及『室外』",
    )
    spacious: bool = Field(
        default=False,
        description="空間是否寬敞。若評論提到『很擠』、『位置少』則為 False。跟停車資訊無關",
    )
    indoor_ac: bool = Field(
        default=False, description="室內是否有冷氣。台灣室內店面通常預設為 True"
    )
    off_leash_possible: bool = Field(
        default=False,
        description="是否有圍欄或專屬區域可放繩跑跳。通常僅限寵物公園或特定農場",
    )
    pet_friendly_floor: bool = Field(
        default=False,
        description="地板是否防滑或適合毛孩行走。若為專業沙龍(pet_care)通常為 True",
    )
    has_shop_pet: bool = Field(
        default=False,
        description="店內是否有店狗或店貓。從評論提及『店長』、『店狗/貓名稱』判定",
    )


class PetService(BaseModel):
    pet_menu: bool = Field(
        default=False,
        description="是否有寵物專屬餐點。若評論提到『毛孩零食』、『狗狗餐』、『狗狗吃飯』、『毛孩零食』、『寵物餐點』則為 True",
    )
    free_water: bool = Field(
        default=False,
        description="是否提供寵物飲水。評論提到『給水碗』、『喝水』則為 True",
    )
    free_treats: bool = Field(default=False, description="是否主動提供免費點心招待毛孩")
    pet_seating: bool = Field(
        default=False,
        description="毛孩是否可上座位。若評論提到『可以坐椅子』、『有寵物墊』、『想一起坐』、『不用坐地板』則為 True",
    )


class PetFeatures(BaseModel):
    rules: PetRules
    environment: PetEnvironment
    services: PetService


class AIAnalysis(BaseModel):
    venue_type: str = Field(description="空間類型判定，如：複合式沙龍、寵物咖啡廳")
    ai_summary: str = Field(description="專業深度分析總結")
    pet_features: PetFeatures
    highlights: List[str] = Field(description="該地點的三個關鍵吸引力")
    warnings: List[str] = Field(description="毛爸媽需要注意的負面反饋或限制")
    ai_rating: float = Field(description="推薦程度", alias="rating")
    model_config = {"populate_by_name": True, "from_attributes": True}
