# Nearby Search Workflow

## Scope

Use this workflow when changing the geospatial nearby search exposed by `GET /api/v1/property/nearby`.

## When To Read This Doc

Read this document when:

- changing nearby request parameters
- changing nearby category filtering
- changing nearby pagination semantics
- changing nearby result ordering or counting behavior
- moving nearby logic across layers

Read `docs/search/architecture.md` when you need the broader structural view of keyword search and nearby search together.

## Entry Points

- Route path: `interface/api/routes/v1/property.py`
- Nearby request schema: `interface/api/schemas/property.py`
- Nearby service entry: `application/property.py::PropertyService.search_nearby`
- Category mapping: `domain/entities/property_category.py`
- Repository query: `infrastructure/mongo/property.py::PropertyRepository.get_nearby`

## Rules

### Flow Boundaries

- Keep the nearby route separate from the natural-language search pipeline.
- Do not add LLM parsing, search-plan generation, or preference tags to nearby unless the product behavior is intentionally changing.
- Keep storage-specific geospatial query details in `infrastructure/mongo/property.py`.
- Keep frontend-facing category translation aligned with the current route contract.

### Request Contract

- `lat` and `lng` are required.
- `radius` is measured in meters.
- `category` is a frontend enum, not a raw MongoDB field.
- `page` and `size` define pagination and must stay compatible with the shared pagination response shape.

If the nearby filter contract changes, update:

- request schema validation
- route-level parameter handling
- category-mapping helpers or repository contract
- all affected unit-test doubles and stubs

### Category Mapping

- Nearby filtering currently expands `PropertyCategoryKey` into Google Places `primary_type` values.
- Keep category expansion centralized in `domain/entities/property_category.py`.
- If a category definition changes, update nearby behavior and overview-category expectations in the same change.

### Query Semantics

- Nearby retrieval is distance-first.
- Soft-deleted properties must stay excluded.
- `total` must stay consistent with the filter used for `items`.
- If the geospatial query changes, verify both page retrieval and total counting semantics.

## Validation

- Keep nearby route unit tests stable.
- If category expansion changes, update the category-domain tests in the same change.
- If repository query semantics change, add or update repository-level unit tests close to `tests/unit/infrastructure/test_mongo_property.py`.
- If shared property contracts change, run the relevant full unit suite before finishing, not only targeted tests.

Minimum nearby-focused coverage should include:

- one test for request-to-service parameter translation
- one test for category expansion behavior
- one test for any new repository query semantics if filters, ordering, or counting change

## Related Files

- `docs/search/architecture.md`
- `interface/api/routes/v1/property.py`
- `interface/api/schemas/property.py`
- `application/property.py`
- `domain/entities/property_category.py`
- `infrastructure/mongo/property.py`
- `tests/unit/adapters/fastapi/test_property.py`
- `tests/unit/domain/test_property_category.py`
- `tests/unit/infrastructure/test_mongo_property.py`
