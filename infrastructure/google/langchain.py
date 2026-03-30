import logging

from infrastructure.runtime_warnings import apply_runtime_warning_filters

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

apply_runtime_warning_filters()


logger = logging.getLogger(__name__)


def geocode_landmark_with_llm(llm: ChatGoogleGenerativeAI, landmark_name: str):
    if landmark_name == "101":
        landmark_name = "台北101"
    geo_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一個座標轉換 API。請輸出 JSON 陣列：[經度, 緯度]。"),
            ("human", "{landmark_name}"),
        ]
    )
    try:
        coords = (geo_prompt | llm | JsonOutputParser()).invoke(
            {"landmark_name": landmark_name}
        )
        if isinstance(coords, list) and len(coords) == 2:
            return landmark_name, coords
        else:
            return landmark_name, None
    except Exception as e:
        logger.error(f"Error geocoding landmark {landmark_name}: {e}")
        return landmark_name, None
