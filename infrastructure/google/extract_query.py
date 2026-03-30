import json
import logging
from typing import List, Optional

from infrastructure.runtime_warnings import apply_runtime_warning_filters

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from domain.entities.property import PropertyEntity, PropertyFilterCondition

apply_runtime_warning_filters()

logger = logging.getLogger(__name__)


class PreferenceTag(BaseModel):
    key: str = Field(
        description="標籤的鍵值，格式為 '欄位名_preference'，例如 'address_preference'"
    )
    label: str = Field(
        description="標籤的顯示文字，例如 '大安區'、'有寵物餐'、'101 附近'"
    )


class SearchIntent(BaseModel):
    mongo_query: dict = Field(
        description=(
            "MongoDB 篩選物件。必須包含類型篩選（如 {{'primary_type': 'lodging'}}）。"
            "注意：此處禁止包含地理座標數字，但必須包含地點類型與布林標籤。"
        )
    )
    matched_fields: List[str] = Field(
        description="這次查詢涉及的原始欄位名稱清單，例如：['pet_menu', 'indoor_ac', 'location']"
    )
    preferences: List[PreferenceTag] = Field(
        description="根據使用者意圖生成的標籤列表。每個標籤包含 key (欄位_preference) 與 label (顯示文字)。"
    )
    min_rating: float = Field(
        default=0.0,
        description="最低評分。預設 0.0。只有當用戶提到『推薦、高品質、評價好、熱門』時才提高門檻。",
    )
    landmark_context: Optional[str] = Field(
        None,
        description="地標名稱。若使用者說『附近』、『我周邊』且未指名地標，請填入 'CURRENT_LOCATION'。",
    )
    travel_time_limit_min: Optional[int] = Field(
        None, description="使用者提到的車程限制（分鐘）。例如：'一小時' -> 60"
    )
    search_radius_meters: int = Field(
        default=5000,
        description="搜尋半徑（公尺）。若使用者提到『附近』預設 2000，提到『區域』預設 5000",
    )
    explanation: str = Field(description="對使用者的推薦理由")


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一個 MongoDB 專家。請根據 PropertyEntity 結構，將需求轉換為精準的 SearchIntent 物件。

### 🚨 絕對禁令 (CRITICAL) 🚨 ###
1. **禁止在 address 搜尋類型關鍵字**：
   - **禁止** 將『餐廳類型、食物、服務名稱』（如：火鍋、咖啡、民宿、洗澡）放入 `address` 的 $regex 中。
   - ❌ 錯誤範例：{{ "address": {{ "$regex": "火鍋" }} }}
   - ✅ 正確做法：將這類關鍵字轉換為 `primary_type`（如：'hot_pot_restaurant'）。
   - **`address` 欄位僅限用於正式行政區（大安區）或路名（中山路）。**

2. **禁止自行生成座標**：
   - **禁止** 在 `mongo_query` 中生成 `location` 欄位或任何經緯度數字。
   - 具體地點請統一填入 `landmark_context`。

### 車程與距離換算規則 ###
- **車程意圖**：若提到『車程、開車多久』，請估算並填入 `search_radius_meters`：
    - 『一小時』：40000 (40公里)。
    - 『半小時/30分鐘』：20000 (20公里)。
    - 『15分鐘』：10000 (10公里)。
- **動作**：`landmark_context` 設為 "CURRENT_LOCATION"，並在 `matched_fields` 加入 "location"。

### 地理位置判定法則 ###
1. **地標優先 (Landmark-First Policy)**：
   - 除非 100% 確定是行政區或路名，否則一律視為地標。
   - **地標/景點** (如 101, 日月潭, 九族)：`landmark_context` = "名稱", `matched_fields` 加入 "location"。
   - **當前位置** (如 附近, 我周邊)：`landmark_context` = "CURRENT_LOCATION", `matched_fields` 加入 "location"。
   - **標籤**：{{ "key": "location_preference", "label": "地標名 附近" 或 "我的附近" }}。

2. **行政區/路名 (僅限 100% 確定時)**：
   - **動作**：在 `mongo_query` 中使用 {{ "address": {{ "$regex": "關鍵字" }} }}。
   - **標籤**：{{ "key": "address_preference", "label": "區域名稱" }}。

### 類型與功能匹配策略 ###
1. **類型匹配 (primary_type)**：
   - 提到咖啡廳、下午茶、甜點 -> 'cafe'
   - 提到火鍋、燒肉、早午餐、餐廳 -> 'restaurant' (或更細分的 hot_pot_restaurant 等)
   - 提到民宿、旅館、住宿 -> 'lodging'
   - 提到看醫生、獸醫 -> 'veterinary_care'
   - 標籤：{{ "key": "primary_type_preference", "label": "類別名稱" }}。

2. **功能篩選**：
   - 使用 `effective_pet_features` 下的點號路徑布林欄位。
   - 標籤：{{ "key": "欄位末端名_preference", "label": "功能簡稱" }}。

### 評價觸發規則 (嚴格執行) ###
- **預設狀態**：`min_rating` 預設為 0.0。
- **僅在使用者明確要求時才觸發**：
  - 提到『推薦、高品質、評價好、好停車』：`min_rating` = 3.8，並加入 {{ "key": "high_rating_preference", "label": "優選高評價" }}。
  - 提到『頂級、最好』：`min_rating` = 4.0。
  - **若使用者僅說『公園』，不包含『推薦』或『好店』等形容詞，則 min_rating 必須保持 0.0。**

### PropertyEntity 結構定義 ###
{entity_schema}

{format_instructions}""",
        ),
        ("user", "{user_input}"),
    ]
)


parser = PydanticOutputParser(pydantic_object=SearchIntent)
entity_info = json.dumps(PropertyEntity.model_json_schema(), ensure_ascii=False)


def extract_query(
    llm: ChatGoogleGenerativeAI, user_input: str
) -> PropertyFilterCondition:
    chain = prompt | llm | parser
    return chain.invoke(
        {
            "user_input": user_input,
            "entity_schema": entity_info,
            "format_instructions": parser.get_format_instructions(),
        }
    )
