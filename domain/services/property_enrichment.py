from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

from domain.entities.enrichment import AnalysisSource
from domain.entities.property import (
    PropertyEntity,
    PropertyFilterCondition,
    PointLocation,
)


class IEnrichmentProvider(ABC):
    @abstractmethod
    def create_property_by_name(self, property_name: str) -> AnalysisSource: ...

    @abstractmethod
    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity: ...

    @abstractmethod
    def extract_search_criteria(self, query: str) -> PropertyFilterCondition: ...

    @abstractmethod
    def geocode_landmark(self, landmark_name: str) -> Tuple[str, Tuple[float, float] | None]: ...


    def generate_query(self, intent: PropertyFilterCondition, user_coords: Optional[tuple[float, float]], map_coords: Optional[tuple[float, float]]) -> dict:
        final_query = intent.mongo_query.copy()

        if intent.min_rating and intent.min_rating > 0:
            final_query["rating"] = {"$gte": intent.min_rating}

        target_coordinates = None
        if intent.landmark_context == "CURRENT_LOCATION":
            #FIXME: consider about user_coords case
            target_coordinates = user_coords
        elif intent.landmark_context:
            display_name, landmark_coords = self.geocode_landmark(intent.landmark_context)
            if landmark_coords:
                target_coordinates = landmark_coords
        else:
            target_coordinates = map_coords

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


