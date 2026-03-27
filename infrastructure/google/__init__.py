from abc import ABC

from domain.entities.enrichment import AnalysisSource
from domain.entities.property import PropertyEntity
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.google.place_api import (
    search_basic_information_by_name,
    get_place_details,
)
from infrastructure.google.vertex import distill_property_insights


class GoogleEnrichmentProvider(IEnrichmentProvider):
    def create_property_by_name(
        self, property_name: str
    ) -> PropertyEntity:

        basic_info = search_basic_information_by_name(property_name)
        insight_info = get_place_details(basic_info)
        information = AnalysisSource.from_parts(basic_info, insight_info)
        return distill_property_insights(information)
