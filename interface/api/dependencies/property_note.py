from fastapi import Depends

from application.property_note import PropertyNoteService
from interface.api.dependencies.db import (
    get_property_repository,
    get_user_repository,
)


def get_property_note_service(
    user_repo=Depends(get_user_repository),
    property_repo=Depends(get_property_repository),
) -> PropertyNoteService:
    return PropertyNoteService(user_repo=user_repo, property_repo=property_repo)
