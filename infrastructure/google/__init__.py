from google.oauth2 import service_account
import vertexai
from langchain_google_genai import ChatGoogleGenerativeAI

from domain.entities.enrichment import AnalysisSource
from domain.entities.property import PropertyEntity, PropertyFilterCondition
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.config import settings
from infrastructure.google.extract_query import extract_query
from infrastructure.google.langchain import geocode_landmark_with_llm
from infrastructure.google.place_api import get_place_details, search_basic_information_by_name
from infrastructure.google.vertex import distill_property_insights


class GoogleEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, client, collection_name):
        creds = service_account.Credentials.from_service_account_file(
            settings.google.service_account_file,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        vertexai.init(
            project=settings.google.project_id,
            location=settings.google.location,
            credentials=creds,
        )

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            project=settings.google.project_id,
            location=settings.google.location,
            credentials=creds,
            temperature=0,
            model_kwargs={"response_mime_type": "application/json"},
        )

    def create_property_by_name(self, property_name: str) -> AnalysisSource:
        basic_info = search_basic_information_by_name(property_name)
        insight_info = get_place_details(basic_info)
        return AnalysisSource.from_parts(basic_info, insight_info)

    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity:
        return distill_property_insights(source)

    def extract_search_criteria(self, query: str) -> PropertyFilterCondition:
        return extract_query(self.llm, query)

    def geocode_landmark(self, landmark_name: str):
        display_name, coordinates = geocode_landmark_with_llm(self.llm, landmark_name)
        return display_name, coordinates
