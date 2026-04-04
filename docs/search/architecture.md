# Search and Recommendation Flow

## Scope

This document describes the structure, responsibilities, and design constraints of the search feature.

Read `docs/search/guide-search-overview.md` when you want a human-oriented walkthrough with diagrams and examples before reading implementation details.

## When To Read This Doc

Read this document when:

- deciding where search logic should live
- changing query interpretation boundaries across layers
- changing nearby search responsibilities
- changing ranking, filter assembly, or search execution modes
- reviewing whether a search change respects the project architecture

Read `docs/search/workflow-optimization.md` for execution rules and `docs/search/workflow-nearby.md` for nearby-specific validation requirements.

## Entry Points

- Search route: `GET /api/v1/property`
- Nearby route: `GET /api/v1/property/nearby`
- Search service: `application/property.py::PropertyService.search_by_keyword`
- Nearby service: `application/property.py::PropertyService.search_nearby`
- Search rules and ranking:
  - `application/property_search/rules.py`
  - `application/property_search/ranking.py`
  - `application/property_search/hybrid.py`
- Search planning and prompts:
  - `infrastructure/search/pipeline.py`
  - `infrastructure/search/prompts.py`
  - `infrastructure/search/merge.py`
- Property repository: `infrastructure/mongo/property.py`
- Enrichment integration:
  - `domain/services/property_enrichment.py`
  - `infrastructure/google/vertex.py`
  - `infrastructure/google/place_api.py`

## Responsibilities

### Route Layer

- Accept search and nearby request parameters.
- Normalize request shape before entering application services.
- Keep HTTP and schema concerns in `interface/`.
- Avoid placing search decision policy directly in route handlers.

### Application Layer

- Orchestrate query interpretation, execution-mode selection, reranking, and hybrid merge behavior.
- Keep business-facing search rules in `application/property_search/`.
- Own search behavior that would still be meaningful without FastAPI, MongoDB, or LangGraph.

### Infrastructure Layer

- Implement the LLM-backed search planner and prompt wiring.
- Implement repository persistence and geospatial query details.
- Keep vendor integration, prompt text, Mongo query execution, and adapter glue out of `application/`.

### Persistence and Enrichment Contracts

- Persist normalized property data that search depends on.
- Expose repository methods for semantic query execution, lexical retrieval, and nearby retrieval.
- Reuse stored enrichment fields at query time instead of regenerating recommendations on every search request.

## Design Constraints

### Search Execution Modes

- The runtime may return `keyword_search`, `semantic_search`, or `hybrid_search`.
- Keyword retrieval is a first-class execution mode, not only a fallback.
- Hybrid execution is intentionally lookup-first and may short-circuit on strong lexical matches.

### Query Interpretation Boundaries

- Natural-language interpretation belongs to the search planner and application search modules, not to route handlers.
- Category, feature, quality, address, landmark, and time-window interpretation should stay out of persistence adapters.
- Nearby search remains separate from the natural-language search planner unless product behavior explicitly changes.

### Geographic Behavior

- Keyword search may use normalized user or map coordinates, landmark geocoding, and explicit distance constraints.
- Address-first queries should not silently inherit map-center geo filtering when the address expression is the primary geographic constraint.
- Nearby search is distance-first and uses the stored GeoJSON location field plus category expansion.

### Ranking and Recommendation

- Runtime ranking is heuristic and application-owned.
- Search quality depends on ingestion-time AI enrichment and query-time interpretation.
- If ranking strategy evolves, keep ranking policy separate from prompt wording where possible.

### Data Model Coupling

- Search depends on derived fields in `PropertyEntity`, including `location`, `rating`, `is_open`, and `op_segments`.
- If those derived fields or their generation rules change, validate search behavior in the same change.

## Related Files

- `docs/search/guide-search-overview.md`
- `docs/search/workflow-optimization.md`
- `docs/search/workflow-nearby.md`
- `application/property.py`
- `application/property_search/ranking.py`
- `application/property_search/rules.py`
- `application/property_search/hybrid.py`
- `infrastructure/search/pipeline.py`
- `infrastructure/search/prompts.py`
- `infrastructure/search/merge.py`
- `infrastructure/mongo/property.py`
- `domain/entities/property.py`
- `domain/entities/property_category.py`
