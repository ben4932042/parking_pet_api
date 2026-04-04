import hashlib
from collections.abc import Callable

from application.property_search.cache_policy import (
    normalize_search_query,
    should_cache_search_plan,
)
from domain.entities.search import SearchPlan
from domain.entities.search_plan_cache import SearchPlanCacheEntity
from domain.repositories.search_plan_cache import ISearchPlanCacheRepository


class SearchPlanWorkflow:
    def __init__(
        self,
        *,
        planner: Callable[[str], SearchPlan],
        version: str,
        cache_repo: ISearchPlanCacheRepository | None = None,
    ):
        self.planner = planner
        self.version = version
        self.cache_repo = cache_repo

    @staticmethod
    def build_cache_key(version: str, normalized_query: str) -> str:
        payload = f"{version}\n{normalized_query}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def extract(self, query: str) -> SearchPlan:
        normalized_query = normalize_search_query(query)
        cache_key = self.build_cache_key(self.version, normalized_query)

        if self.cache_repo is not None:
            cached = self.cache_repo.touch(cache_key)
            if cached is not None:
                return SearchPlan.model_validate(cached.plan_payload)

        plan = self.planner(query)
        if self.cache_repo is None or not should_cache_search_plan(plan):
            return plan

        self.cache_repo.save(
            SearchPlanCacheEntity(
                cache_key=cache_key,
                query_text=query,
                normalized_query=normalized_query,
                version=self.version,
                plan_payload=plan.model_dump(mode="json"),
                hit_count=0,
            )
        )
        return plan
