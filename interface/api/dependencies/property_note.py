from fastapi import Depends

from application.property_note import PropertyNoteService
from interface.api.dependencies.db import (
    get_property_note_repository,
    get_property_repository,
)


def get_property_note_service(
    note_repo=Depends(get_property_note_repository),
    property_repo=Depends(get_property_repository),
) -> PropertyNoteService:
    return PropertyNoteService(note_repo=note_repo, property_repo=property_repo)
