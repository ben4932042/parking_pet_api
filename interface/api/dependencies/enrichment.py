from fastapi import Depends

from infrastructure.google import GoogleEnrichmentProvider
from infrastructure.mongo import MongoDBClient
from infrastructure.mongo.landmark_cache import LandmarkCacheRepository
from infrastructure.mongo.search_plan_cache import SearchPlanCacheRepository
from interface.api.dependencies.db import (
    get_db_client,
    get_landmark_cache_repository,
    get_search_plan_cache_repository,
)


def get_enrichment_provider(
    client: MongoDBClient = Depends(get_db_client),
    landmark_cache_repo: LandmarkCacheRepository = Depends(
        get_landmark_cache_repository
    ),
    search_plan_cache_repo: SearchPlanCacheRepository = Depends(
        get_search_plan_cache_repository
    ),
) -> GoogleEnrichmentProvider:
    return GoogleEnrichmentProvider(
        client=client,
        collection_name="property_v3",
        landmark_cache_repo=landmark_cache_repo,
        search_plan_cache_repo=search_plan_cache_repo,
    )
