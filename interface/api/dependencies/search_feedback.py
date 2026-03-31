from fastapi import Depends

from application.search_feedback import SearchFeedbackService
from interface.api.dependencies.db import get_search_feedback_repository


def get_search_feedback_service(
    repo=Depends(get_search_feedback_repository),
) -> SearchFeedbackService:
    return SearchFeedbackService(repo=repo)
