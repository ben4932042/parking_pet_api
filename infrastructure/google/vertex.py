import json
import logging
import vertexai
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel, GenerationConfig
from infrastructure.config import settings

logger = logging.getLogger(__name__)

creds = service_account.Credentials.from_service_account_file(
    settings.google.service_account_file
)

vertexai.init(
    project=settings.google.project_id,
    location=settings.google.location,
    credentials=creds
)


model = GenerativeModel("gemini-2.5-flash-lite")

def analyze_full_place_data_vertex(place_data):
    data_json_str = json.dumps(place_data, ensure_ascii=False, indent=2)

    prompt = f"""
    請根據以下店家的完整 Google Maps JSON 資料（包含座標、評分、價格等級與評論），產生結構化的分析標籤。

    【輸入數據】:
    {data_json_str}

    【輸出 JSON 欄位要求】:
    1. suitable_for: 適合的對象/場景 (例如: 家庭聚餐, 帶寵物, 深夜食堂)
    2. pros: 核心優點 (根據數據與評論總結)
    3. cons: 潛在缺點或提醒 (例如: 需久候, 價格略高)
    4. signature_items: 推薦必點 (從評論中提取具體菜名)
    5. ai_summary: 50字左右的介紹，盡量只提到店家/地點特色，不要提分數或評論數。
    """

    generation_config = GenerationConfig(
        response_mime_type="application/json",
        temperature=0.2,
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        ai_analysis = json.loads(response.text)
        place_data['ai_analysis'] = ai_analysis
        return place_data

    except Exception as e:
        logger.exception("Failed to analyze place data with Vertex AI, using fallback method. Error", exc_info=True)
        place_data['ai_analysis'] = {"error": f"AI 分析失敗: {str(e)}"}
        return place_data

if __name__ == "__main__":
    from infrastructure.google.place_api import get_new_property_data
    place_name = "鼎泰豐 台北101店"
    new_shop = get_new_property_data(place_name)
    print(analyze_full_place_data_vertex(new_shop))