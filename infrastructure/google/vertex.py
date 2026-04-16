import logging
import vertexai
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, GenerationConfig

from domain.entities.enrichment import AIAnalysis, AnalysisSource
from domain.entities.property import PropertyEntity
from infrastructure.config import settings
from infrastructure.runtime_warnings import apply_runtime_warning_filters

apply_runtime_warning_filters()


logger = logging.getLogger(__name__)

creds = service_account.Credentials.from_service_account_file(
    settings.google.service_account_file
)

vertexai.init(
    project=settings.google.project_id,
    location=settings.google.location,
    credentials=creds,
)


model = GenerativeModel("gemini-2.5-flash")


def distill_property_insights(source: AnalysisSource) -> PropertyEntity:
    """
    將整個 place_data 字典丟進 Vertex AI 進行深度分析
    """
    data_json = source.model_dump_json(indent=2)

    prompt = f"""
    # Role: Senior Pet Space Analysis Expert
    
    You are a professional consultant specializing in pet-friendly environments. Your task is to generate a structured report **IN TRADITIONAL CHINESE** based on the provided JSON data.
    ---
    ### 【Strategy 1: Segment-Specific Analysis (Logic)】
    Identify the **Segment** of the venue and apply the corresponding criteria for internal evaluation:
    
    #### 1. Professional Medical & Grooming (專業醫療與美容)
    * **Core Focus:** Expertise, hygiene (odor control), pet handling gentleness, and price transparency.
    * **Exclusion Clause:** **DO NOT** list "No pet menu" or "Pets not allowed on sofas" as warnings. These are irrelevant to this segment.
    
    #### 2. Outdoor & Recreation (戶外休閒與公園)
    * **Core Focus:** Grass maintenance, safety fencing, water/waste bin availability, and space.
    * **Exclusion Clause:** **DO NOT** list "No air conditioning" or "No pet food" as warnings.
    
    #### 3. Dining & Hospitality (寵物友善餐飲與旅宿)
    * **Core Focus:** Ground rules (leash/stroller/on-seat), pet menus, and stroller accessibility.
    * **Warning Trigger:** If pets must remain strictly in crates/bags at all times, note it as a limitation.
    
    ---
    
    ### 【Strategy 2: Data Inference & Rating】
    1.  **Handling Nulls:** `null` is missing data, not "False". Use reviews to infer the truth.
    2.  **AI Rating (0.0 - 5.0):** * Rating must be segment-weighted (e.g., Hygiene is 50% of the score for Hospitals).
        * **Logic Lock:** If serious issues like "medical injury" or "extreme filth" are mentioned, the rating **must be below 2.0**.
    
    ---
    
    ### 【Task Requirements (Output in Traditional Chinese)】
    
    請依照以下格式輸出繁體中文報告：
    
    1.  **業態定位 (Venue Positioning)**：明確標註（例如：專業醫療美容、戶外休閒、寵物友善餐飲）。
    2.  **AI 綜合總結 (AI Summary)**：200字內，以「毛爸媽視角」出發。嚴禁提及「五星好評」、「評論數」等字眼，專注於描述空間體感、專業度與氛圍。
    3.  **亮點與警示 (Highlights & Warnings)**：
        * **亮點 (Highlights)**：根據業態挑選 3 個最重要的優點。
        * **警示 (Warnings)**：必須是「具備負面價值」的項目。嚴禁跨行業要求（例如：不要抱怨公園沒有寵物餐）。
    4.  **寵物友善評分 (AI Rating)**：基於業態權重計算出的 0.0 - 5.0 分數。
    
    ---
    
    ### 【Input Data】:
    {data_json}
    """

    generation_config = GenerationConfig(
        response_mime_type="application/json",
        response_schema=AIAnalysis.model_json_schema(),
        temperature=0.1,
    )

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
        ai_analysis = AIAnalysis.model_validate_json(response.text)

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
        logger.error(f"Error generating AI analysis: {e}")
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
