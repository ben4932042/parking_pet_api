# Search and Recommendation Flow

## Scope

This document describes how the current project implements search and recommendation for properties, with a focus on the keyword-based search flow exposed by `GET /api/v1/property`.

The goal of the feature is not full-text retrieval in the search-engine sense. The current implementation is closer to an AI-assisted structured filter pipeline:

1. Interpret a natural-language query.
2. Convert it into a MongoDB filter.
3. Apply optional geographic proximity.
4. Sort matching documents by internal rating.
5. Fall back to a simple keyword lookup only when the search plan explicitly requests it.

## Main Entry Points

### `GET /api/v1/property`

This is the main search endpoint.

Accepted query parameters:

- `query`: natural-language search text.
- `user_lat`, `user_lng`: current user location.
- `map_lat`, `map_lng`: map center location.

Response shape:

- `status`
- `preferences`: UI-oriented tags extracted from the query
- `results`: property overview objects

### `GET /api/v1/property/nearby`

This endpoint is a pure geospatial search and does not use the LLM intent parser. It filters by distance from a point and optionally by `primary_type`.

### `POST /api/v1/property`

This endpoint is part of the data ingestion path rather than the runtime search path. It fetches Google Place data, generates AI analysis, and persists the normalized property document that later participates in search and recommendation.

## High-Level Architecture

The feature spans four layers:

- API layer: receives request parameters and returns response DTOs.
- Application layer: orchestrates query understanding, repository lookup, and fallback behavior.
- Enrichment layer: uses Google Gemini / Vertex AI to interpret user intent and to enrich place data.
- Persistence layer: stores and queries `PropertyEntity` documents in MongoDB.

Relevant files:

- `interface/api/routes/v1/property.py`
- `application/property.py`
- `domain/services/property_enrichment.py`
- `infrastructure/google/search.py`
- `infrastructure/google/__init__.py`
- `infrastructure/mongo/property.py`
- `domain/entities/property.py`
- `domain/entities/enrichment.py`
- `infrastructure/google/vertex.py`
- `infrastructure/google/place_api.py`

## Runtime Search Flow

### 1. HTTP request enters the property route

`GET /api/v1/property` receives the free-text query plus two optional coordinate sources:

- user location
- map center

The route forwards them to `PropertyService.search_by_keyword(...)`.

Important detail: the route now normalizes coordinates before calling the service. If either latitude or longitude is missing, that coordinate source is treated as unavailable instead of building a partially empty geo tuple.

### 2. Natural-language query is converted into a structured intent

`PropertyService.search_by_keyword(...)` calls:

- `enrichment_provider.extract_search_plan(q)`

The concrete implementation is `GoogleEnrichmentProvider.extract_search_plan(...)`, which uses the LangGraph-based search pipeline defined in `infrastructure/google/search.py`.

The pipeline produces a structured `SearchPlan` containing:

- `route`: whether the query should use keyword or semantic retrieval
- `filter_condition`: the normalized `PropertyFilterCondition`
- `semantic_extraction`: summarized address/category/feature/quality extraction
- `warnings`: low-confidence parsing signals
- `used_fallback` and `fallback_reason`

### 3. Intent generation rules

The prompt strongly constrains the model to avoid common mistakes.

#### Type mapping

Natural-language category words are mapped to `primary_type` values, for example:

- coffee / dessert / afternoon tea -> `cafe`
- hot pot -> `hot_pot_restaurant`
- restaurant -> `restaurant`
- lodging / hotel -> `lodging`
- vet / doctor -> `veterinary_care`
- pet grooming -> `pet_care`
- pet supplies -> `pet_store`
- park / hiking / dog park -> `park`

#### Address vs. landmark separation

The prompt explicitly forbids putting POI keywords such as `Taipei 101` or `Sun Moon Lake` into `address` regex filters unless the term is clearly an administrative district or street name.

The intended rules are:

- district / road -> `address` regex
- landmark / attraction -> `landmark_context`
- “near me” -> `landmark_context = CURRENT_LOCATION`

#### Feature filters

Pet-related requirements should map to boolean fields under `ai_analysis.pet_features`, not to free-text search.

This means recommendation quality depends heavily on the AI enrichment done at ingestion time.

#### Rating triggers

The system uses `min_rating` as a coarse recommendation gate.

The neutral default is now `0.0`. Rating filters are only added when the parsed intent explicitly asks for recommendation-oriented quality thresholds.

### 4. Final Mongo query is assembled

After the LLM returns a `PropertyFilterCondition`, `generate_query(...)` merges the structured conditions into a final MongoDB filter.

This step:

- starts from `intent.mongo_query`
- adds `rating >= min_rating` when `min_rating > 0`
- chooses a geographic anchor
- injects a geospatial `location` filter using `$nearSphere`

Geographic anchor precedence is:

1. `CURRENT_LOCATION` -> normalized `user_coords`
2. explicit landmark -> geocode landmark with LLM
3. otherwise -> normalized `map_coords`

If the chosen coordinates are missing or incomplete, the geo filter is skipped.

If landmark geocoding fails, the search now degrades gracefully to a non-landmark query instead of raising an exception.

### 5. MongoDB executes the structured query and the application reranks the results

`PropertyRepository.find_by_query(...)` runs:

- `collection.find(query)`
- `.sort("rating", -1)`

MongoDB still returns a first-pass candidate list ordered by rating, but the application layer now performs a second-pass rerank before returning results.

The current rerank combines:

- AI-derived rating
- overall pet-feature density
- requested pet-feature matches from the query
- distance score when a geo anchor exists
- small bonuses for exact type match and requested open-now match

This is still a heuristic ranker rather than a learned recommendation model, but it is no longer pure `rating desc`.

### 6. Fallback to regex keyword search

If the structured query returns zero documents, the service falls back to `get_by_keyword(q)`.

The fallback query is:

- case-insensitive regex on `name`
- case-insensitive regex on `address`

The service currently keeps only the first matched result.

This fallback is important because it allows direct place-name lookup when the intent parser produces filters that are too narrow or too abstract.

## Where Recommendation Signals Come From

The project has two different recommendation stages.

### Stage A: offline-ish enrichment during property creation

When a new property is created through `POST /api/v1/property`, the system:

1. searches Google Places by name
2. fetches place details and reviews
3. sends the combined source data to Vertex AI
4. generates a structured `AIAnalysis`
5. stores the resulting `PropertyEntity`

The stored analysis includes:

- `venue_type`
- `ai_summary`
- `pet_features.rules`
- `pet_features.environment`
- `pet_features.services`
- `highlights`
- `warnings`
- `ai_rating`

This `ai_rating` becomes the document `rating` used later in query-time ranking.

### Stage B: online query-time filtering and sorting

At search time, the runtime system does not regenerate recommendations from reviews. Instead, it reuses the stored enrichment fields:

- `primary_type`
- `ai_analysis.pet_features.*`
- `rating`
- `location`
- `address`

So the search system is recommendation-aware mainly because the database already contains AI-generated pet-friendliness features and ratings.

## Data Model Notes

`PropertyEntity` contains several derived fields that matter for search:

- `location`: generated from longitude/latitude for geospatial search
- `rating`: copied from `ai_analysis.ai_rating`
- `is_open`: computed from opening hours at model-validation time
- `op_segments`: generated from opening hours for open/closed evaluation

This means search behavior depends not only on raw stored data but also on Pydantic model validation side effects.

## Nearby Search Flow

`GET /api/v1/property/nearby` is simpler than keyword search.

It:

- optionally filters `primary_type` using `types_str`
- applies MongoDB `$near`
- paginates results with `skip` and `limit`
- counts total results using a separate `$geoWithin` filter

This endpoint is proximity-first and recommendation-second. It does not interpret natural language and does not use `preferences` tags.

## Response Semantics

The keyword search response returns:

- `preferences`: frontend-facing tags that explain how the query was interpreted
- `results`: a list of overview entities

The tags are important because they are the only explicit trace of the system’s intent interpretation shown to the client.

## Current Strengths

- Clear separation between API, application, enrichment, and repository concerns.
- Good use of structured model output instead of free-form LLM text.
- Practical fallback from intent-based search to direct keyword lookup.
- Search is grounded in a normalized property model rather than calling Google live for every query.
- Recommendation logic is specialized for pet-related use cases through `AIAnalysis`.
- The search path now guards against missing coordinate pairs and landmark geocoding failures.

## Current Limitations and Risks

The following issues are still present in the current implementation and should be understood as part of the existing behavior.

### 1. Fallback only returns the first regex match

When the structured query fails, the fallback truncates results to a single item. This is acceptable for exact place-name lookup, but it is weak for ambiguous place names or partial keywords.

### 2. Ranking is heuristic, not learned

The ranking layer now blends multiple signals, but it is still a hand-tuned heuristic formula. It does not yet use click feedback, popularity history, or learned relevance signals.

### 3. Search quality depends heavily on prompt behavior

The query parser is strongly guided by prompt rules, which is practical, but it also means regressions can be introduced by prompt drift or model behavior changes unless the project maintains regression tests around expected parsed intents.

## Suggested Future Improvements

If the team wants the feature to evolve beyond the current implementation, the most impactful next steps would be:

1. Preserve multiple fallback matches instead of only the first one.
2. Tune the heuristic weights with real query examples instead of keeping them static.
3. Add more regression coverage around query parsing outputs, not just query assembly safeguards.
4. Separate intent extraction from ranking strategy so recommendation tuning does not require prompt tuning.
5. Add popularity or engagement signals once the project has usable behavioral data.

## Summary

The current search and recommendation feature is best described as an AI-assisted MongoDB filtering system backed by AI-enriched property metadata.

Its recommendation quality depends on two things:

- how well the ingestion pipeline converts Google place data and reviews into `AIAnalysis`
- how well the query parser converts natural language into correct MongoDB filters

At runtime, recommendation is implemented primarily through:

- structured filtering
- optional geospatial narrowing
- heuristic reranking over rating, pet-friendly signals, and distance
- regex fallback when structured search fails

That design is pragmatic and understandable, but it is still an early-stage recommendation system rather than a fully developed ranking engine.
