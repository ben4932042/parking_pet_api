# Codebase Review: Proposed Tasks

## 1) Typo fix task
- **Issue found:** In the property creation endpoint, a TODO comment says `handle duplicate property event`, but this appears to be a wording typo (`event` vs `error`).
- **Proposed task:** Update the TODO to `handle duplicate property error` (or remove TODO and file a typed exception ticket) so intent is clear for future maintainers.
- **Reference:** `interface/api/routes/v1/property.py`.

## 2) Bug fix task
- **Issue found:** `PropertyService.get_details` raises `ValueError("Property not found")` when no record exists, but the route handler checks `if not prop` and raises 404 only in that branch. Because `ValueError` is raised first, the request can surface as a 500 instead of a 404.
- **Proposed task:** Make service/router behavior consistent by either:
  - returning `None` from `get_details` and letting the route map it to 404, **or**
  - raising a domain `NotFoundError` and mapping it centrally in exception handlers.
- **References:** `application/property.py`, `interface/api/routes/v1/property.py`, `interface/api/exceptions/error.py`.

## 3) Code comment / documentation discrepancy task
- **Issue found:** `MongoDBClient` is documented as a singleton-style manager, but the dependency provider constructs a new `MongoDBClient()` per dependency resolution.
- **Proposed task:** Resolve the mismatch by either implementing an actual singleton/shared lifecycle instance in DI, or revising the class docstring/comments to reflect per-request instantiation.
- **References:** `infrastructure/mongo/__init__.py`, `interface/api/dependencies/db.py`, `interface/api/lifespan.py`.

## 4) Test improvement task
- **Issue found:** There are no focused regression tests around computed `location` generation in `PropertyEntity`; current validator uses falsy checks and can treat valid coordinates like `0.0` as missing.
- **Proposed task:** Add a unit test that builds `PropertyEntity` with latitude/longitude of `0.0` and asserts `location` is still generated (`{"type": "Point", "coordinates": [0.0, 0.0]}`). This test will prevent future coordinate-edge regressions.
- **Reference:** `domain/entities/property.py`.
