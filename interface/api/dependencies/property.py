from fastapi import Depends

from application.property import PropertyService
from interface.api.dependencies.db import get_property_repository
from interface.api.dependencies.enrichment import get_enrichment_provider


def get_property_service(repo=Depends(get_property_repository), enrichment_provider=Depends(get_enrichment_provider)) -> PropertyService:

    return PropertyService(repo=repo, enrichment_provider=enrichment_provider)
