from abc import ABC

from domain.entities.property import PropertyEntity
from domain.services.property_enrichment import IEnrichmentProvider
from infrastructure.google.place_api import get_new_property_data
from infrastructure.google.vertex import analyze_full_place_data_vertex


class GoogleEnrichmentProvider(IEnrichmentProvider):
    def create_property_by_name(
        self, property_name: str
    ) -> PropertyEntity:
        result = analyze_full_place_data_vertex(get_new_property_data(property_name))
        return PropertyEntity(**result)
