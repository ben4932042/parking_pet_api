import logging
import math
from typing import Any, List, Optional

from domain.entities import PyObjectId
from domain.entities.property import PropertyDetailEntity, PropertyEntity
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property import IPropertyRepository
from domain.services.property_enrichment import IEnrichmentProvider


logger = logging.getLogger(__name__)


class PropertyService:
    def __init__(
        self,
        repo: IPropertyRepository,
        raw_data_repo: IPlaceRawDataRepository,
        enrichment_provider: IEnrichmentProvider,
    ):
        self.repo = repo
        self.raw_data_repo = raw_data_repo
        self.enrichment_provider = enrichment_provider

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        types: List[str],
        page: int,
        size: int,
    ):
        return await self.repo.get_nearby(lat, lng, radius, types, page, size)

    async def search_by_keyword(
        self,
        q: str,
        user_coords: Optional[tuple[float, float]] = None,
        map_coords: Optional[tuple[float, float]] = None,
    ):
        filter_condition = self.enrichment_provider.extract_search_criteria(q)
        logger.debug(f"Search criteria: {filter_condition}")
        generate_query = self.enrichment_provider.generate_query(
            filter_condition,
            user_coords,
            map_coords,
        )
        logger.debug(f"Generated query: {generate_query}")
        items = await self.repo.find_by_query(generate_query)
        if not items:
            logger.info("No properties found for the given search criteria. try to search by name")
            response = await self.repo.get_by_keyword(q)
            items = response[:1]
        else:
            items = self._rank_search_results(items, generate_query)
        return items, filter_condition

    async def get_overviews_by_ids(self, property_ids: list[str]):
        return await self.repo.get_properties_by_ids(property_ids)

    async def get_details(self, property_id: PyObjectId) -> Optional[PropertyDetailEntity]:
        output: PropertyEntity = await self.repo.get_property_by_id(property_id)
        if output is None:
            return None
        return PropertyDetailEntity(
            id=output.id,
            name=output.name,
            address=output.address,
            latitude=output.latitude,
            longitude=output.longitude,
            types=output.types,
            rating=output.ai_analysis.ai_rating,
            tags=output.ai_analysis.highlights,
            regular_opening_hours=output.regular_opening_hours,
            ai_analysis=output.ai_analysis,
        )

    async def create_property(self, name: str):
        source_data = self.enrichment_provider.create_property_by_name(name)
        await self.raw_data_repo.create(source_data)
        ai_result = self.enrichment_provider.generate_ai_analysis(source_data)
        await self.repo.create(ai_result)
        logging.info(f"Property {name} created successfully")

    def _rank_search_results(self, items: List[PropertyEntity], query: dict) -> List[PropertyEntity]:
        type_filter = query.get("primary_type")
        is_open_required = query.get("is_open") is True
        requested_feature_paths = self._requested_feature_paths(query)
        geo_context = self._extract_geo_context(query)

        return sorted(
            items,
            key=lambda item: self._score_search_result(
                item=item,
                type_filter=type_filter,
                is_open_required=is_open_required,
                requested_feature_paths=requested_feature_paths,
                geo_context=geo_context,
            ),
            reverse=True,
        )

    @staticmethod
    def _score_search_result(
        item: PropertyEntity,
        type_filter: Any,
        is_open_required: bool,
        requested_feature_paths: List[str],
        geo_context: Optional[dict[str, Any]],
    ) -> float:
        rating_score = max(0.0, min((item.ai_analysis.ai_rating or 0.0) / 5.0, 1.0))
        pet_feature_score = PropertyService._pet_feature_score(item)
        requested_feature_score = PropertyService._requested_feature_score(item, requested_feature_paths)
        distance_score = PropertyService._distance_score(item, geo_context)
        type_score = PropertyService._type_score(item, type_filter)
        open_score = 0.05 if is_open_required and item.is_open else 0.0

        return (
            (rating_score * 0.45)
            + (pet_feature_score * 0.20)
            + (requested_feature_score * 0.15)
            + (distance_score * 0.15)
            + type_score
            + open_score
        )

    @staticmethod
    def _type_score(item: PropertyEntity, type_filter: Any) -> float:
        if not type_filter:
            return 0.0

        if isinstance(type_filter, dict) and "$in" in type_filter:
            return 0.05 if item.primary_type in type_filter["$in"] else 0.0

        return 0.05 if item.primary_type == type_filter else 0.0

    @staticmethod
    def _pet_feature_score(item: PropertyEntity) -> float:
        pet_features = item.ai_analysis.pet_features.model_dump()
        bool_values: List[bool] = []

        def _collect(values: Any) -> None:
            if isinstance(values, dict):
                for nested in values.values():
                    _collect(nested)
            elif isinstance(values, bool):
                bool_values.append(values)

        _collect(pet_features)
        if not bool_values:
            return 0.0

        return sum(1 for value in bool_values if value) / len(bool_values)

    @staticmethod
    def _requested_feature_paths(query: dict) -> List[str]:
        return [
            key
            for key, value in query.items()
            if key.startswith("ai_analysis.pet_features.") and isinstance(value, bool)
        ]

    @staticmethod
    def _requested_feature_score(item: PropertyEntity, requested_feature_paths: List[str]) -> float:
        if not requested_feature_paths:
            return 0.0

        matched = sum(
            1
            for path in requested_feature_paths
            if PropertyService._get_nested_value(item.model_dump(), path) is True
        )
        return matched / len(requested_feature_paths)

    @staticmethod
    def _extract_geo_context(query: dict) -> Optional[dict[str, Any]]:
        location_query = query.get("location", {})
        near_query = location_query.get("$nearSphere")
        if not near_query:
            return None

        geometry = near_query.get("$geometry", {})
        coordinates = geometry.get("coordinates")
        max_distance = near_query.get("$maxDistance")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or coordinates[0] is None
            or coordinates[1] is None
            or not max_distance
        ):
            return None

        return {
            "coordinates": (coordinates[0], coordinates[1]),
            "max_distance": max_distance,
        }

    @staticmethod
    def _distance_score(item: PropertyEntity, geo_context: Optional[dict[str, Any]]) -> float:
        if not geo_context:
            return 0.0

        anchor_lng, anchor_lat = geo_context["coordinates"]
        distance_meters = PropertyService._haversine_meters(
            lat1=anchor_lat,
            lng1=anchor_lng,
            lat2=item.latitude,
            lng2=item.longitude,
        )
        max_distance = geo_context["max_distance"]
        if max_distance <= 0:
            return 0.0

        return max(0.0, 1.0 - (distance_meters / max_distance))

    @staticmethod
    def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371000
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    @staticmethod
    def _get_nested_value(payload: dict, path: str) -> Any:
        current: Any = payload
        for key in path.split("."):
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current
