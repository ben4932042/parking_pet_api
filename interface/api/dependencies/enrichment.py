from fastapi import Depends

from infrastructure.google import GoogleEnrichmentProvider
from infrastructure.mongo import MongoDBClient
from infrastructure.mongo.landmark_cache import LandmarkCacheRepository
from interface.api.dependencies.db import (
    get_db_client,
    get_landmark_cache_repository,
)


def get_enrichment_provider(
    client: MongoDBClient = Depends(get_db_client),
    landmark_cache_repo: LandmarkCacheRepository = Depends(
        get_landmark_cache_repository
    ),
) -> GoogleEnrichmentProvider:
    return GoogleEnrichmentProvider(
        client=client,
        collection_name="property_v3",
        landmark_cache_repo=landmark_cache_repo,
    )
