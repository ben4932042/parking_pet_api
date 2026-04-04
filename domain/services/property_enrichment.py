from abc import ABC, abstractmethod
from typing import Optional, Tuple

from domain.entities.enrichment import AnalysisSource
from domain.entities.property import PropertyEntity
from domain.entities.search import PropertyFilterCondition, SearchPlan


class IEnrichmentProvider(ABC):
    @abstractmethod
    def create_property_by_name(self, property_name: str) -> AnalysisSource: ...

    @abstractmethod
    def renew_property_from_details(self, source: AnalysisSource) -> AnalysisSource: ...

    @abstractmethod
    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity: ...

    @abstractmethod
    def extract_search_plan(self, query: str) -> SearchPlan: ...

    @abstractmethod
    def geocode_landmark(
        self, landmark_name: str
    ) -> Tuple[str, Optional[Tuple[float, float]]]: ...

    @staticmethod
    def _normalize_coordinates(
        coords: Optional[tuple[float, float]],
    ) -> Optional[tuple[float, float]]:
        if coords is None or len(coords) != 2:
            return None

        lng, lat = coords
        if lng is None or lat is None:
            return None

        return (lng, lat)

    def generate_query(
        self,
        intent: PropertyFilterCondition,
        user_coords: Optional[tuple[float, float]],
        map_coords: Optional[tuple[float, float]],
    ) -> dict:
        final_query = intent.mongo_query.copy()

        if intent.min_rating and intent.min_rating > 0:
            final_query["rating"] = {"$gte": intent.min_rating}

        target_coordinates = None
        if intent.landmark_context == "CURRENT_LOCATION":
            target_coordinates = self._normalize_coordinates(user_coords)
        elif intent.landmark_context:
            _, landmark_coords = self.geocode_landmark(intent.landmark_context)
            target_coordinates = self._normalize_coordinates(landmark_coords)
        elif "address" not in final_query:
            target_coordinates = self._normalize_coordinates(map_coords)

        if target_coordinates:
            final_query["location"] = {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": list(target_coordinates),
                    },
                    "$maxDistance": intent.search_radius_meters,
                }
            }
        return final_query
