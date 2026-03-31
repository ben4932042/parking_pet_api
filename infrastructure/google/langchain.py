import logging

from infrastructure.runtime_warnings import apply_runtime_warning_filters
from infrastructure.prompt import GEOCODE_LANDMARK_PROMPT

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

apply_runtime_warning_filters()


logger = logging.getLogger(__name__)


def geocode_landmark_with_llm(llm: ChatGoogleGenerativeAI, landmark_name: str):

    geo_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", GEOCODE_LANDMARK_PROMPT),
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
