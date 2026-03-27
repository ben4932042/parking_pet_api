from typing import Optional

from domain.entities import PyObjectId
from domain.entities.property import PropertySummary, PropertyEntity
from domain.repositories.property import IPropertyRepository
from domain.services.property_enrichment import IEnrichmentProvider


class PropertyService:
    def __init__(self, repo: IPropertyRepository, enrichment_provider: IEnrichmentProvider ):
        self.repo = repo
        self.enrichment_provider = enrichment_provider

    async def search_nearby(self, lat: float, lng: float, radius: int,  type: Optional[str], page: int, size: int):
        return await self.repo.get_nearby(lat, lng, radius, type, page, size)

    async def search_by_keyword(self, q: str, type: Optional[str], page: int, size: int):
        return await self.repo.get_by_keyword(q, type, page, size)

    async def get_details(self, property_id: PyObjectId) -> PropertySummary:
        output:PropertyEntity = await self.repo.get_property_by_id(property_id)
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

    async def update_favorite(self, user_id: str, property_id: PyObjectId, is_favorite: bool):
        return await self.repo.toggle_favorite(user_id, property_id, is_favorite)

    async def create_property(self, name: str):
        generate_result = self.enrichment_provider.create_property_by_name(name)
        await self.repo.create(generate_result)
