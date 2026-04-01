from fastapi import Depends

from application.search_history import SearchHistoryService
from interface.api.dependencies.db import get_search_history_repository


def get_search_history_service(
    repo=Depends(get_search_history_repository),
) -> SearchHistoryService:
    return SearchHistoryService(repo=repo)
