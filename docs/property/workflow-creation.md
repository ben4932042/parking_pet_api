# Property Creation

## Scope

This document covers property creation through the property API.

## When To Read This Doc

Read this document when:

- changing the create-or-sync flow
- changing property ingestion behavior
- updating validation or audit expectations for property creation

Read `docs/property/architecture.md` when you need the broader property-layer structure.

## Entry Points

- API route: `POST /property`
- Route module: `interface/api/routes/v1/property.py`
- Service method: `application/property.py::PropertyService.create_property`
- Supporting repository path: `infrastructure/mongo/property.py`
- Supporting enrichment path: `domain/services/property_enrichment.py`

## Rules

The creation flow is a create-or-sync flow:

1. Resolve the input keyword or business name through the enrichment provider.
2. Persist the raw source payload for traceability.
3. Check whether the resolved `place_id` already exists.
4. If the property already exists and is active, sync it instead of creating a duplicate.
5. If the property is soft-deleted, reject the request and require restore first.
6. Generate AI analysis and build the final property entity.
7. Save the property and create an audit log.

- Property creation is keyed by resolved `place_id`, not by the raw input string.
- Manual pet-feature overrides must be preserved during sync.
- A property with `primary_type="unknown"` must not be created.
- Create and sync must both leave an audit trail.

## Validation

- Keep unit tests stable for property creation and sync behavior.
- If create-or-sync behavior changes, update related doubles and fixtures in the same change.
- If the change affects shared property mutation semantics, run the relevant full unit suite before finishing.

## Related Files

- `interface/api/routes/v1/property.py`
- `application/property.py`
- `domain/services/property_enrichment.py`
- `infrastructure/mongo/property.py`
- `tests/unit/application`
