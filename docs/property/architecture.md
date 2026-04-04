# Property Architecture

## Scope

This document describes the structure, responsibilities, and design constraints of the property feature.

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
- Property search helpers:
  - `application/property_search/ranking.py`
  - `application/property_search/rules.py`

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

## Design Constraints

### Property Ownership

- Property creation, sync, mutation, restore, and audit behavior belong in `application/property.py`.
- Property note behavior belongs in `application/property_note.py`.
- Route handlers should coordinate request and response shapes, not own property decision policy.

### Persistence Boundaries

- MongoDB query details, update operators, and storage normalization belong in `infrastructure/mongo/property.py`.
- Persistence adapters should not own business rules such as audit requirements, restore semantics, or manual-override policy.

### Shared Property Invariants

- Property identity is anchored by normalized storage identifiers such as `place_id` and internal `property_id`, depending on the flow.
- Soft delete is a business invariant and must stay aligned across search, detail, mutation, and restore paths.
- Audit coverage is part of property behavior, not an optional adapter concern.

### Cross-Feature Boundaries

- Search-specific query interpretation and ranking logic belong in `application/property_search/`, not in route modules or persistence adapters.
- Favorite orchestration may compose user and property behavior, but property overviews and note-aware ordering should still be served through property-facing application services.
- User-private notes are a property-adjacent feature and should not leak note-joining logic into repository storage methods.

## Related Files

- `docs/property/workflow-creation.md`
- `docs/property/workflow-management.md`
- `docs/property/workflow-favorite.md`
- `interface/api/routes/v1/property.py`
- `application/property.py`
- `application/property_note.py`
- `application/property_search/ranking.py`
- `application/property_search/rules.py`
- `infrastructure/mongo/property.py`
- `interface/api/schemas/property.py`
