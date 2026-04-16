from application.property_search.planner import SearchPlanWorkflow
from infrastructure.runtime_warnings import apply_runtime_warning_filters

from google.oauth2 import service_account
import vertexai
from langchain_google_genai import ChatGoogleGenerativeAI

from domain.entities.enrichment import AnalysisSource
from domain.entities.landmark_cache import LandmarkCacheEntity
from domain.entities.parking import NearbyParkingCandidate
from domain.entities.property import PropertyEntity
from domain.repositories.landmark_cache import ILandmarkCacheRepository
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.config import settings
from infrastructure.google.place_api import (
    geocode_landmark_by_name,
    get_basic_information_by_place_id,
    get_place_details,
    search_nearby_parking,
    search_basic_information_by_name,
)
from infrastructure.search.pipeline import extract_search_plan
from infrastructure.google.vertex import distill_property_insights

apply_runtime_warning_filters()


class GoogleEnrichmentProvider(IEnrichmentProvider):
    def __init__(
        self,
        landmark_cache_repo: ILandmarkCacheRepository | None = None,
        search_plan_workflow: SearchPlanWorkflow | None = None,
    ):
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
            model="gemini-2.5-flash",
            project=settings.google.project_id,
            location=settings.google.location,
            credentials=creds,
            temperature=0,
            response_mime_type="application/json",
        )
        self.landmark_cache_repo = landmark_cache_repo
        self.search_plan_workflow = search_plan_workflow

    @staticmethod
    def _build_landmark_cache_key(landmark_name: str) -> str:
        return " ".join(landmark_name.split()).strip().casefold()

    def create_property_by_name(self, property_name: str) -> AnalysisSource:
        basic_info = search_basic_information_by_name(property_name)
        insight_info = get_place_details(basic_info)
        return AnalysisSource.from_parts(basic_info, insight_info)

    def renew_property_from_basic(self, place_id: str) -> AnalysisSource:
        basic_info = get_basic_information_by_place_id(place_id)
        insight_info = get_place_details(basic_info)
        return AnalysisSource.from_parts(basic_info, insight_info)

    def renew_property_from_details(self, source: AnalysisSource) -> AnalysisSource:
        insight_info = get_place_details(source)
        return AnalysisSource.from_parts(source, insight_info)

    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity:
        return distill_property_insights(source)

    async def extract_search_plan(self, query: str):
        if self.search_plan_workflow is None:
            return extract_search_plan(self.llm, query)
        return await self.search_plan_workflow.extract(query)

    async def geocode_landmark(self, landmark_name: str):
        normalized_name = " ".join(landmark_name.split()).strip()
        if not normalized_name:
            return landmark_name, None

        cache_key = self._build_landmark_cache_key(normalized_name)
        if self.landmark_cache_repo is not None:
            cached = await self.landmark_cache_repo.get_by_key(cache_key)
            if cached is not None:
                return cached.display_name, cached.coordinates

        display_name, coordinates = geocode_landmark_by_name(normalized_name)

        if self.landmark_cache_repo is not None:
            longitude = coordinates[0] if coordinates is not None else None
            latitude = coordinates[1] if coordinates is not None else None
            await self.landmark_cache_repo.save(
                LandmarkCacheEntity(
                    cache_key=cache_key,
                    query_text=normalized_name,
                    display_name=display_name,
                    longitude=longitude,
                    latitude=latitude,
                )
            )

        return display_name, coordinates

    def search_nearby_parking(
        self,
        lat: float,
        lng: float,
        *,
        radius: float = 2000.0,
        max_result_count: int = 20,
    ) -> list[NearbyParkingCandidate]:
        return search_nearby_parking(
            lat=lat,
            lng=lng,
            radius=radius,
            max_result_count=max_result_count,
        )
