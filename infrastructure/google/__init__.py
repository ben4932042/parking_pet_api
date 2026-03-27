from abc import ABC

from domain.entities.enrichment import AnalysisSource
from domain.entities.property import PropertyEntity, PropertySearchResultEntity
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.google.langchain import search_properties
from infrastructure.google.place_api import (
    search_basic_information_by_name,
    get_place_details,
)
from infrastructure.google.vertex import distill_property_insights


class GoogleEnrichmentProvider(IEnrichmentProvider):
    def __init__(self, client, collection_name):
        self.collection = client.get_collection(collection_name)
    def create_property_by_name(
        self, property_name: str
    ) -> AnalysisSource:

        basic_info = search_basic_information_by_name(property_name)
        insight_info = get_place_details(basic_info)
        return AnalysisSource.from_parts(basic_info, insight_info)

    def generate_ai_analysis(self, source: AnalysisSource) -> PropertyEntity:
        return distill_property_insights(source)


    async def search_by_chat(self, query: str, size: int) -> PropertySearchResultEntity:
        result = await search_properties(query=query, size=size, collection=self.collection )
        return PropertySearchResultEntity(**result)