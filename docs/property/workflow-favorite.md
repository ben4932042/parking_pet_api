# Property Favorite Workflow

## Scope

This document covers user-facing property favorite flows.

## When To Read This Doc

Read this document when:

- changing favorite add or remove behavior
- changing favorite status or favorite list APIs
- adjusting how favorites interact with property overview or note ordering

Read `docs/property/architecture.md` when you need the broader property-layer structure.

## Entry Points

- Add or remove a favorite: `PUT /user/favorite/{property_id}`
- Get favorite status: `GET /user/favorite/{property_id}`
- List favorite properties: `GET /user/favorite`
- Route module: `interface/api/routes/v1/user.py`
- User service method: `application/user.py::UserService.update_favorite_property`
- Property service methods:
  - `application/property.py::PropertyService.get_overviews_by_ids`
  - `application/property.py::PropertyService.get_noted_property_ids`
- User repository contract: `domain/repositories/user.py`
- User repository implementation: `infrastructure/mongo/user.py`
- User schema and entity:
  - `interface/api/schemas/user.py`
  - `domain/entities/user.py`

## Rules

- Favorite state is stored on the user record as `favorite_property_ids`.
- Adding a favorite must be idempotent and use set semantics, not duplicate inserts.
- Removing a favorite must remove only the target property id from the user record.
- Favorite status is derived from whether the target property id exists in `current_user.favorite_property_ids`.
- Favorite list responses must load property overviews from the property service, not duplicate property read logic inside the user repository.
- Favorite list ordering should prioritize items that already have user notes.
- Favorite flow orchestration stays in route and application layers, while persistence details stay in `infrastructure/`.

## Validation

- Keep unit tests stable for favorite update, status, and list behavior.
- If favorite contracts change, update related stubs, fixtures, and repository doubles in the same change.
- If favorite list behavior changes, validate note-priority ordering in the related FastAPI adapter tests.

## Related Files

- `interface/api/routes/v1/user.py`
- `application/user.py`
- `application/property.py`
- `domain/entities/user.py`
- `domain/repositories/user.py`
- `infrastructure/mongo/user.py`
- `interface/api/schemas/user.py`
- `tests/unit/application/test_user_service.py`
- `tests/unit/adapters/fastapi/test_user.py`
