from fastapi import Depends

from infrastructure.google import GoogleEnrichmentProvider
from infrastructure.mongo import MongoDBClient
from interface.api.dependencies.db import get_db_client


def get_enrichment_provider(client: MongoDBClient = Depends(get_db_client)) -> GoogleEnrichmentProvider:
    return GoogleEnrichmentProvider(client=client, collection_name="property_v2")