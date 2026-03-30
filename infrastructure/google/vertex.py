import logging

from infrastructure.runtime_warnings import apply_runtime_warning_filters

apply_runtime_warning_filters()

import vertexai
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, GenerationConfig

from domain.entities.enrichment import AIAnalysis, AnalysisSource
from domain.entities.property import PropertyEntity
from infrastructure.config import settings


logger = logging.getLogger(__name__)

creds = service_account.Credentials.from_service_account_file(
    settings.google.service_account_file
)

vertexai.init(
    project=settings.google.project_id,
    location=settings.google.location,
    credentials=creds,
)


model = GenerativeModel("gemini-2.5-flash-lite")


def distill_property_insights(source: AnalysisSource) -> PropertyEntity:
    """
    將整個 place_data 字典丟進 Vertex AI 進行深度分析
    """
    data_json = source.model_dump_json(indent=2)

    prompt = f"""
    你現在是一位資深的「寵物空間分析專家」。請根據提供的 JSON 資料產出結構化報告。

    【核心策略：資料補全與推斷】：
    1. **處理 null (None)**：`null` 代表 Google 資料庫缺少標記，**絕對不等於 False**。
    2. **推斷順序**：
       - **優先：評論內容**。若評論提到「提供水碗」、「店狗熱情」、「好停車」、「環境擠」，請強制更新對應的特徵布林值。
       - **次之：產業分類**。`primary_type` 為 'pet_care' 時，`allows_dogs` 預設為 True。
       - **再次：環境語境**。若評論提到「甜點、提拉米蘇」，即使 types 沒寫，也請在總結中指出其具備「複合式咖啡廳」屬性。
    3. **處理衝突**：若 API 標註 `allows_dogs: null` 但評論說「禁止大型犬進入」，請在 `ai_summary` 提醒家長特定限制，並將 `allows_dogs` 設為 False（以評論為準）。
    【核心策略：場域特化分析】：
     1. **場域判定 (Crucial)**：
        - 若 `primary_type` 或評論顯示為 **「專業服務」**(如：美容、醫療、住宿)，請以「專業度、細心度、安全性」為分析核心。
        - 若顯示為 **「餐飲/休閒」**(如：咖啡廳、餐廳、公園)，請以「舒適度、餐點、落地規則」為核心。

     2. **排除非必要警告 (Noise Reduction)**：
        - **禁止「跨行業比對」**：若判定為「專業美容沙龍」，不要在 `warnings` 提到「沒有寵物餐」或「不能上座位」，因為這不符合該業態的常規。
        - **警告必須具備「負面價值」**：只有當該店明顯低於同行標準（如：沙龍環境髒亂、餐廳極度擁擠、階梯過多導致推車完全無法進入）時，才列入 `warnings`。
    【ai_rating 評分邏輯 (重點)】：
    請根據你填寫的 **PetFeatures** 內容，計算出 0.0 - 5.0 的綜合評分：

    - **基礎設施分 (PetEnvironment & PetService)**：
        - 擁有 `indoor_ac`(冷氣)、`spacious`(寬敞)、`pet_friendly_floor`(友善地板) 為加分項。
        - 提供 `pet_menu`(寵物餐)、`free_water`(水碗)、`pet_seating`(可上座) 是極高加分項。

    - **規則友善度 (PetRules)**：
        - `allow_on_floor`(可落地) 權重最高。若需 `stroller_required`(強迫推車) 或禁止落地，評分應適度下修。

    - **服務與氛圍 (從評論推斷)**：
        - 美容師或店員的耐心程度、環境有無異味（清潔度）。
   - **友善度**：店家對寵物的包容心（是否可上座、是否提供水碗、店員態度）。

    - **扣分與參考**：
        - 若有 `stairs`(階梯) 且無電梯（推車不便）需扣分。
        - 參考 Google 的原始 `rating` 作為服務品質基底，但「寵物友善程度」由上述特徵決定。
    - **邏輯一致性檢查**：`ai_rating` 必須與 `PetFeatures` 的布林值正相關。若多項服務為 False，評分不得高於 4.0。

    【任務要求】：
    - **ai_summary**：200字內，毛爸媽視角。嚴禁提及「星等」、「評論數」、「排名」但盡可能正面表述。
    - **風格定位**：判斷其為「專業美容沙龍」、「寵物友善餐飲」或「複合式空間」。
    - **細節挖掘**：從評論中找尋「清潔味」、「細心度」、「空間是否擁擠」。
    - **highlights/warnings**：根據 PetFeatures 的優缺點挑選 3 個最重要的項目。
    - **ai_rating**：基於上述特徵連動計算出的 0.0 - 5.0 分數。
    - **分析一致性**：確保 `highlights` 提到的優點在 `PetFeatures` 中對應為 True。

    【輸入數據】:
    {data_json}
    """

    # --- 2. Vertex AI 強大功能：設定 JSON 輸出模式 ---
    generation_config = GenerationConfig(
        response_mime_type="application/json",
        response_schema=AIAnalysis.model_json_schema(),
        temperature=0.1,
    )

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        ai_analysis = AIAnalysis.model_validate_json(response.text)

        # 建立 PropertyEntity
        # 這裡利用了 Pydantic 的自動校驗，會觸發你寫的 model_validator
        entity = PropertyEntity(
            _id=source.place_id,
            name=source.display_name,
            place_id=source.place_id,
            latitude=source.latitude,
            longitude=source.longitude,
            regular_opening_hours=source.regular_opening_hours,
            address=source.address,
            primary_type=source.primary_type or "unknown",
            ai_analysis=ai_analysis,
        )
        return entity

    except Exception as e:
        print(f"Vertex AI 分析失敗: {e}")
        raise e



if __name__ == "__main__":
    from infrastructure.google.place_api import (
        search_basic_information_by_name,
        get_place_details,
    )

    place_name = "鼎泰豐 台北101店"
    basic_info = search_basic_information_by_name(place_name)
    insight_info = get_place_details(basic_info)
    information = AnalysisSource.from_parts(basic_info, insight_info)
    print(distill_property_insights(information))
