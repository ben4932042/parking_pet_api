from fastapi import Depends

from application.property import PropertyService
from interface.api.dependencies.embedding import get_embedding_provider
from interface.api.dependencies.db import (
    get_place_raw_data_repository,
    get_property_audit_repository,
    get_property_note_repository,
    get_property_repository,
)
from interface.api.dependencies.enrichment import get_enrichment_provider


def get_property_service(
    repo=Depends(get_property_repository),
    raw_data_repo=Depends(get_place_raw_data_repository),
    audit_repo=Depends(get_property_audit_repository),
    note_repo=Depends(get_property_note_repository),
    enrichment_provider=Depends(get_enrichment_provider),
    embedding_provider=Depends(get_embedding_provider),
) -> PropertyService:
    return PropertyService(
        repo=repo,
        raw_data_repo=raw_data_repo,
        audit_repo=audit_repo,
        note_repo=note_repo,
        enrichment_provider=enrichment_provider,
        embedding_provider=embedding_provider,
    )
