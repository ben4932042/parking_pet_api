from domain.entities.search import SearchPlan

from application.property_search.constants import (
    NON_SEARCH_ROUTE_REASON,
    PROMPT_INJECTION_ROUTE_REASON,
)


def normalize_search_query(query: str) -> str:
    return " ".join(query.split()).casefold()


def should_cache_search_plan(plan: SearchPlan) -> bool:
    return plan.route_reason not in {
        PROMPT_INJECTION_ROUTE_REASON,
        NON_SEARCH_ROUTE_REASON,
    }
