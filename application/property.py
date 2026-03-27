import logging
from typing import Optional

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
        type: Optional[str],
        page: int,
        size: int,
    ):
        return await self.repo.get_nearby(lat, lng, radius, type, page, size)

    async def search_by_keyword(self, q: str, size: int):
        return await self.enrichment_provider.search_by_chat(q, size)

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
