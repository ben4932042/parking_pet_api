import logging
from typing import Optional, List

from domain.entities import PyObjectId
from domain.entities.property import PropertySummary, PropertyEntity
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

    async def search_by_keyword(self, q: str, user_coords: Optional[tuple[float, float]] = None, map_coords: Optional[tuple[float, float]] = None):
        filter_condition = self.enrichment_provider.extract_search_criteria(q)
        logger.debug(f"Search criteria: {filter_condition}")
        generate_query = self.enrichment_provider.generate_query(filter_condition, user_coords, map_coords)
        logger.debug(f"Generated query: {generate_query}")
        items = await self.repo.find_by_query(generate_query)
        if len(items) == 0:
            logger.info("No properties found for the given search criteria. try to search by name")
            response = await self.repo.get_by_keyword(q)
            items = response[:1]
        return items, filter_condition

    async def get_overviews_by_ids(self, property_ids: list[str]):
        return await self.repo.get_properties_by_ids(property_ids)

    async def get_details(self, property_id: PyObjectId) -> PropertySummary:
        output: PropertyEntity = await self.repo.get_property_by_id(property_id)
        if output is None:
            raise ValueError("Property not found")
        return PropertySummary(
            id=output.id,
            name=output.name,
            address=output.address,
            latitude=output.latitude,
            longitude=output.longitude,
            types=[output.primary_type],
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
