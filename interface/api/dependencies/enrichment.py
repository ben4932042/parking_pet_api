from fastapi import Depends

from application.property_search.planner import SearchPlanWorkflow
from infrastructure.google import GoogleEnrichmentProvider
from infrastructure.mongo.landmark_cache import LandmarkCacheRepository
from infrastructure.mongo.search_plan_cache import SearchPlanCacheRepository
from infrastructure.config import settings
from infrastructure.search.pipeline import extract_search_plan
from interface.api.dependencies.db import get_landmark_cache_repository, get_search_plan_cache_repository


def get_enrichment_provider(
    landmark_cache_repo: LandmarkCacheRepository = Depends(
        get_landmark_cache_repository
    ),
    search_plan_cache_repo: SearchPlanCacheRepository = Depends(
        get_search_plan_cache_repository
    ),
) -> GoogleEnrichmentProvider:
    provider = GoogleEnrichmentProvider(
        landmark_cache_repo=landmark_cache_repo,
    )
    provider.search_plan_workflow = SearchPlanWorkflow(
        planner=lambda query: extract_search_plan(provider.llm, query),
        version=settings.search.search_plan_cache_version,
        cache_repo=search_plan_cache_repo,
    )
    return provider
