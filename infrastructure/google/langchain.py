import logging
import warnings

import vertexai
from google.oauth2 import service_account
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from infrastructure.config import settings

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module="langchain_google_vertexai"
)


logger = logging.getLogger(__name__)

creds = service_account.Credentials.from_service_account_file(
    settings.google.service_account_file,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],  # 加入這一行
)

vertexai.init(
    project=settings.google.project_id,
    location=settings.google.location,
    credentials=creds,
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    project=settings.google.project_id,
    location=settings.google.location,
    credentials=creds,
    temperature=0,
    model_kwargs={"response_mime_type": "application/json"},
)


def geocode_landmark_with_llm(landmark_name: str):
    if landmark_name == "101":
        landmark_name = "台北101"
    geo_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一個精準的座標轉換 API。請輸出 JSON 陣列：[經度, 緯度]。"),
            ("human", "{landmark_name}"),
        ]
    )
    try:
        coords = (geo_prompt | llm | JsonOutputParser()).invoke(
            {"landmark_name": landmark_name}
        )
        return coords if isinstance(coords, list) and len(coords) == 2 else None
    except:
        return None


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一位 MongoDB 查詢與寵物友善專家。請將需求轉換為包含「條件降級」的 JSON。

【資料庫精準路徑】：
- 基礎: `name`, `address`, `primary_type`, `rating`
- 落地規則: `ai_analysis.pet_features.rules.allow_on_floor`
- 戶外設施: `ai_analysis.pet_features.environment.outdoor_seating`
- 寵物餐: `ai_analysis.pet_features.services.pet_menu`

【類型展開 (primary_type)】：
- 餐廳/咖啡：$in ["restaurant", "cafe", "bakery", "coffee_shop", "diner"]
- 戶外/景點：$in ["park", "hiking_area", "tourist_attraction", "dog_park", "farm"]
- 寵物用品：$in ["pet_store", "store"]

【降級計畫規則 (Fallback Strategy)】：
1. 第一層 (最嚴格)：包含所有條件 (地點 + 距離 + 戶外 + 落地 + 推薦)。
2. 第二層 (放寬環境)：保持核心地點與落地規則，但「移除」戶外、冷氣、評價等環境設施限制。
3. 第三層 (最寬鬆)：移除所有布林限制，僅保留核心類型 (如: 只要是餐廳) 並拉大搜尋半徑。
【核心禁令 - 違反則程式崩潰】：
1. MQL 嚴禁包含任何地理查詢（如 location, address, $near, $geoWithin）。
2. MQL 嚴禁包含任何數學運算式（如 / 或 *），數值必須為純數字。
3. 嚴禁對 `nearby_target` 的名稱進行 $regex 搜尋。
【輸出 JSON 格式規定】：
{{
  "nearby_target": "地標名稱" 或 null,
  "original_tags": ["標籤1", "標籤2"], // 使用者原始輸入的所有關鍵需求
  "query_plans": [
    {{
      "plan_name": "嚴格條件",
      "active_tags": ["地標", "1km", "餐飲", "戶外", "落地"], // 💡 該計畫實際採用的標籤
      "mql": {{ "完整 MongoDB 查詢" }},
      "radius_meters": 1000
    }},
    {{
      "plan_name": "放寬環境限制",
      "active_tags": ["地標", "3km", "餐飲", "落地"], // 💡 拿掉不滿足的標籤
      "mql": {{ "移除設施欄位的查詢" }},
      "radius_meters": 3000
    }},
    {{
      "plan_name": "最大範圍搜尋",
      "active_tags": ["地標", "5km", "餐飲"], // 💡 僅剩核心標籤
      "mql": {{ "僅保留類型查詢" }},
      "radius_meters": 5000
    }}
  ]
}}

【核心禁令】：只要有 `nearby_target`，MQL 中嚴格禁止對該地標名稱進行 $regex 搜尋。""",
        ),
        ("human", "{user_query}"),
    ]
)

mongo_query_chain = prompt | llm | JsonOutputParser()


async def search_properties(query: str, size: int = 20, collection=None):
    try:
        # 1. 取得 AI 解析結果
        ai_result = mongo_query_chain.invoke({"user_query": query})
        if not ai_result:
            return {"status": "failed", "results": [], "original_tags": [query]}

        raw_original_tags = ai_result.get("original_tags", [])
        nearby_target = ai_result.get("nearby_target")
        query_plans = ai_result.get("query_plans", [])

        # 2. 獲取座標
        coords = geocode_landmark_with_llm(nearby_target) if nearby_target else None

        all_results = []
        seen_ids = set()  # 用來記錄已經抓過的 ID，防止重複
        last_active_tags = []

        # 3. 遍歷計畫，湊齊 size
        for plan in query_plans:
            # 如果已經湊夠了，直接跳出
            if len(all_results) >= size:
                break

            mql = plan.get("mql", {})
            mql.pop("location", None)
            mql.pop("address", None)

            # 排除掉已經在 all_results 裡的資料
            if seen_ids:
                mql["_id"] = {"$nin": list(seen_ids)}

            radius_meters = plan.get("radius_meters", 3000)

            if coords:
                mql["location"] = {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": coords,
                        },
                        "$maxDistance": radius_meters,
                    }
                }

            remaining_size = size - len(all_results)

            current_results = (
                await collection.find(mql)
                .limit(remaining_size)
                .to_list(length=remaining_size)
            )

            if current_results:
                for r in current_results:
                    r["_id"] = str(r["_id"])
                    if r["_id"] not in seen_ids:
                        all_results.append(r)
                        seen_ids.add(r["_id"])

                last_active_tags = plan.get("active_tags")

        if all_results:
            return {
                "status": "success",
                "original_tags": raw_original_tags,
                "active_tags": last_active_tags,
                "results": all_results,
            }

        return {"status": "failed", "original_tags": raw_original_tags, "results": []}

    except Exception as e:
        logger.exception(f"Search failed: {e}")
        return {"status": "error", "results": [], "message": str(e)}
