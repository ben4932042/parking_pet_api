# Property Architecture

## Scope

This document describes the main boundaries and responsibilities of the property feature.

## When To Read This Doc

Read this document when:

- deciding where new property logic should live
- changing property APIs or mutation flows
- adding new property-related workflows
- changing property-facing favorite behavior that combines user state with property overviews

Read the workflow documents when you need the execution rules for a specific flow.

## Entry Points

- API routes: `interface/api/routes/v1/property.py`
- Main service: `application/property.py`
- Repository dependency: `infrastructure/mongo/property.py`
- Property note service: `application/property_note.py`
- Schemas: `interface/api/schemas/property.py`

## Responsibilities

### Route Layer

- Accept HTTP inputs and validate request shape.
- Convert service outputs into response DTOs.
- Stay thin and delegate business behavior to services.

### Application Layer

- Own property creation, sync, mutation, audit, and search orchestration.
- Keep business rules in service methods and application-level helpers.
- Preserve business invariants such as audit coverage and soft-delete behavior.

### Persistence Layer

- Persist normalized property data.
- Provide query and mutation methods for property retrieval and storage.
- Keep storage concerns out of route and workflow logic.

## Main Flows

- Search and nearby retrieval
- Property creation and sync
- Favorite add, remove, status, and list retrieval
- Manual pet-feature override
- Soft delete and restore
- Audit-log retrieval
- User private notes

## Related Files

- `interface/api/routes/v1/property.py`
- `application/property.py`
- `application/property_search.py`
- `application/property_search_rules.py`
- `infrastructure/mongo/property.py`
- `interface/api/schemas/property.py`
