from fastapi import APIRouter, Depends
from starlette import status

from application.search_feedback import SearchFeedbackService
from domain.entities.audit import ActorInfo
from interface.api.dependencies.search_feedback import get_search_feedback_service
from interface.api.dependencies.user import get_request_actor
from interface.api.schemas.search_feedback import (
    SearchFeedbackCreateRequest,
    SearchFeedbackCreateResponse,
)

router = APIRouter(prefix="/search-feedback")


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=SearchFeedbackCreateResponse,
    summary="Create search feedback",
)
async def create_search_feedback(
    payload: SearchFeedbackCreateRequest,
    service: SearchFeedbackService = Depends(get_search_feedback_service),
    actor: ActorInfo = Depends(get_request_actor),
):
    feedback = await service.create_feedback(
        query=payload.query,
        response_type=payload.response_type,
        reason=payload.reason,
        preferences=payload.preferences,
        result_ids=payload.result_ids,
        actor=actor,
    )
    return {
        "status": "ok",
        "feedback_id": str(feedback.id),
    }
