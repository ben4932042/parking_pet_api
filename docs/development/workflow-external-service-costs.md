# External Service Cost Reference

## Scope

This document records the current request-level cost profile for Google Places API and Vertex AI usage in this repository.

## When To Read This Doc

Read this document when:

- estimating the operating cost of property creation
- estimating the operating cost of search traffic
- changing Google Places field masks
- changing Gemini / Vertex prompts or search-planning fanout

## Entry Points

- Property creation flow: `application/property.py::PropertyService.create_property`
- Property enrichment provider: `infrastructure/google/__init__.py`
- Places integration: `infrastructure/google/place_api.py`
- Vertex enrichment call: `infrastructure/google/vertex.py`
- Search planning graph: `infrastructure/search/pipeline.py`

## Rules

- Treat the numbers in this document as a working reference, not a billing contract.
- Re-check official pricing before making product or budgeting decisions because Google pricing can change.
- If a field mask changes, update this document in the same change because Places SKU classification can also change.
- If prompt structure or search-planning fanout changes, update the Vertex call-count assumptions in the same change.

## Current Cost Reference

All estimates below were derived from the current implementation and official pricing pages reviewed on April 3, 2026.

### Property Creation

`POST /property` uses the following external calls during a successful create:

- `1` Google Places Text Search request
- `1` Google Places Details request
- `1` Vertex Gemini request for AI analysis

Current implementation details:

- `search_basic_information_by_name()` requests fields such as `paymentOptions`, `parkingOptions`, `delivery`, and `dineIn`, which places the request in `Places API Text Search Enterprise + Atmosphere`.
- `get_place_details()` requests fields such as `reviews`, `allowsDogs`, `outdoorSeating`, `reservable`, `parkingOptions`, and related atmosphere-style data, which places the request in `Places API Place Details Enterprise + Atmosphere`.
- `distill_property_insights()` uses `gemini-2.5-flash-lite` on Vertex AI.

Estimated cost per successful create:

| Component | Calls per request | Estimated unit cost (USD) | Estimated request cost (USD) |
|---|---:|---:|---:|
| Places API Text Search Enterprise + Atmosphere | 1 | `$0.040` | `$0.040` |
| Places API Place Details Enterprise + Atmosphere | 1 | `$0.025` | `$0.025` |
| Vertex AI Gemini 2.5 Flash-Lite analysis | 1 | `$0.00024 ~ $0.00030` | `$0.00024 ~ $0.00030` |
| Total |  |  | `$0.06524 ~ $0.06530` |

Special case:

- If the property already exists and neither review content nor `user_rating_count` changed, the flow skips the Vertex analysis call. In that case, the Places cost still applies and the total request cost is about `$0.065`.

### Search Requests

`GET /property` does not have a single fixed external-cost profile. Vertex and Places usage depend on the query shape and cache state.

#### Search cost table

| Query shape | Vertex calls | Places calls | Estimated total cost (USD) | Notes |
|---|---:|---:|---:|---|
| Rule-resolved search | 0 | 0 | `$0` | Example: a query fully handled by rule-based parsing |
| Name / brand lookup | 2 | 0 | `~$0.00056` | Typical short lookup such as a direct place or brand name |
| Free-form semantic search | 4 | 0 | `~$0.00115` | Typical natural-language intent parsing path |
| Landmark search with cache hit | 0 or 4 | 0 | `$0` or `~$0.00115` | Depends on whether the query still needs LLM parsing |
| Landmark search with cache miss and no LLM parsing | 0 | 1 Text Search | `~$0.04000` | Geocoding reuses Places Text Search |
| Landmark search with cache miss and LLM parsing | 4 | 1 Text Search | `~$0.04115` | Places geocoding plus semantic planning |

#### Search-planning notes

- Search planning uses `gemini-2.5-flash-lite` through `ChatGoogleGenerativeAI`.
- The search graph can short-circuit to zero Vertex calls when rule-based extraction is sufficient.
- The search graph can also fan out into multiple structured parsing calls. The common high-water path is four Vertex calls for one query.
- Landmark geocoding uses the Places integration, not Vertex, and is cached through `LandmarkCacheRepository`.

## Request Cost Tables

### Combined request-cost table

This table includes both Places API and Vertex AI costs.

| Item | API / scenario | Vertex calls | Other Google calls | Estimated cost per request (USD) | Notes |
|---|---|---:|---:|---:|---|
| Property creation | `POST /property` successful create | 1 | Places Text Search `1` + Places Details `1` | `$0.06524 ~ $0.06530` | Nearly fixed cost profile |
| Property creation | `POST /property` existing property with unchanged reviews | 0 | Places Text Search `1` + Places Details `1` | `$0.06500` | Vertex analysis is skipped |
| Search | Rule-resolved search | 0 | 0 | `$0` | Fully handled by rule-based parsing |
| Search | Name / brand lookup | 2 | 0 | `~$0.00056` | Example: a direct place or brand name |
| Search | Free-form semantic search | 4 | 0 | `~$0.00115` | Natural-language search-planning path |
| Search | Landmark search with cache hit | 0 or 4 | 0 | `$0` or `~$0.00115` | Depends on whether LLM parsing still runs |
| Search | Landmark search with cache miss and no LLM parsing | 0 | Places Text Search `1` | `~$0.04000` | Geocoding only |
| Search | Landmark search with cache miss and LLM parsing | 4 | Places Text Search `1` | `~$0.04115` | Geocoding plus semantic planning |

### Volume-cost table

This table includes both Places API and Vertex AI costs.

| Item | 1 request | 100 requests | 1000 requests |
|---|---:|---:|---:|
| Property creation `POST /property` successful create | `$0.06524 ~ $0.06530` | `$6.52 ~ $6.53` | `$65.24 ~ $65.30` |
| Property creation `POST /property` existing property with unchanged reviews | `$0.06500` | `$6.50` | `$65.00` |
| Search: rule-resolved | `$0` | `$0` | `$0` |
| Search: name / brand lookup | `~$0.00056` | `~$0.056` | `~$0.56` |
| Search: free-form semantic search | `~$0.00115` | `~$0.115` | `~$1.15` |
| Search: landmark cache miss without LLM parsing | `~$0.04000` | `~$4.00` | `~$40.00` |
| Search: landmark cache miss with LLM parsing | `~$0.04115` | `~$4.12` | `~$41.15` |

### Vertex-only table

This table excludes Places API costs and isolates only Vertex AI usage.

| Item | Vertex calls | Estimated Vertex cost per request (USD) | 100 requests | 1000 requests |
|---|---:|---:|---:|---:|
| Property creation successful create | 1 | `$0.00024 ~ $0.00030` | `$0.024 ~ $0.030` | `$0.24 ~ $0.30` |
| Property creation existing property with unchanged reviews | 0 | `$0` | `$0` | `$0` |
| Search: rule-resolved | 0 | `$0` | `$0` | `$0` |
| Search: name / brand lookup | 2 | `~$0.00056` | `~$0.056` | `~$0.56` |
| Search: free-form semantic search | 4 | `~$0.00115` | `~$0.115` | `~$1.15` |

### Unit-cost breakdown

| Billing component | Estimated unit cost (USD) |
|---|---:|
| Places API Text Search Enterprise + Atmosphere | `$0.040` |
| Places API Place Details Enterprise + Atmosphere | `$0.025` |
| Vertex AI property-analysis call | `$0.00024 ~ $0.00030` |
| Vertex AI per-call cost in lookup-style search | `~$0.00028` |

## Verification Notes

- These estimates were cross-checked against the current field masks in `infrastructure/google/place_api.py`.
- Vertex call-count assumptions were cross-checked against the current search graph in `infrastructure/search/pipeline.py`.
- Token-cost estimates for Vertex were approximated from the current prompts and representative payload sizes, so real billing can vary with prompt length, review volume, and model output length.

## Sources

- Vertex AI pricing: <https://cloud.google.com/vertex-ai/generative-ai/pricing>
- Google Maps Platform pricing: <https://developers.google.com/maps/billing-and-pricing/pricing>
- Places Text Search field / SKU reference: <https://developers.google.com/maps/documentation/places/web-service/text-search>
- Places Details field / SKU reference: <https://developers.google.com/maps/documentation/places/web-service/place-details>

## Related Files

- `application/property.py`
- `infrastructure/google/__init__.py`
- `infrastructure/google/place_api.py`
- `infrastructure/google/vertex.py`
- `infrastructure/search/pipeline.py`
