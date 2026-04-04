# Search Overview Guide

## Purpose

This guide explains the current search and recommendation flow in a human-oriented way.

Use it when you want to understand the big picture before reading implementation details.

## When To Read This Doc

Read this document when:

- onboarding to the search feature
- explaining the flow to another developer or stakeholder
- understanding why a query became keyword, semantic, hybrid, or nearby
- you want diagrams and examples before reading the agent-facing docs

Read `docs/search/architecture.md` for the agent-facing structural boundaries and `docs/search/workflow-optimization.md` for execution rules when changing search behavior.

## Diagram

### Main Search Flow

```mermaid
flowchart TD
    A["GET /api/v1/property<br/>query, user/map coords, radius"] --> B["extract_search_plan(q)"]
    B --> C["SearchPlan<br/>execution_modes"]

    C --> D{"execution_modes"}

    D -->|keyword| E["Run keyword lexical retrieval<br/>name / aliases / address"]
    D -->|semantic| F["Build semantic Mongo query"]
    D -->|semantic + keyword| G["Hybrid mode: keyword-first"]

    G --> H["Run keyword lexical retrieval"]
    H --> I["Filter keyword hits with semantic constraints<br/>when semantic execution is also active"]
    I --> J{"Top keyword result is exact<br/>and still satisfies semantic filters?"}

    J -->|yes| K["Return keyword-first result"]
    J -->|no| L["Run semantic retrieval"]

    F --> M["repo.find_by_query(...)"]
    L --> M

    M --> N["rank_search_results(...)"]
    N --> O{"Started in hybrid mode?"}
    O -->|no| P["Return semantic_search"]
    O -->|yes| Q["Merge keyword + semantic"]
    Q --> R["Keyword results stay above semantic hits"]
    R --> S["Return hybrid_search"]

    E --> T["Return keyword_search"]
```

### Nearby Search Flow

```mermaid
flowchart TD
    A["GET /api/v1/property/nearby"] --> B["Validate lat/lng, radius, page, size"]
    B --> C{"category provided?"}
    C -->|yes| D["Expand frontend category<br/>to primary_type list"]
    C -->|no| E["Distance-only query"]
    D --> F["Mongo $near query"]
    E --> F
    F --> G["Paginate results"]
    G --> H["Count total with geo filter"]
    H --> I["Attach has_note if user exists"]
    I --> J["Return paginated nearby response"]
```

## Walkthrough

The current search system is closer to an AI-assisted structured filter pipeline than to a traditional full-text search engine.

The main flow works like this:

1. The API receives a natural-language query.
2. The search planner decides whether the query should run keyword search, semantic search, or both.
3. Semantic search turns the query into structured filters.
4. Keyword search looks for direct lexical matches in name, aliases, and address.
5. Hybrid mode tries keyword first, then runs semantic retrieval only when needed.
6. The final response returns one of `keyword_search`, `semantic_search`, or `hybrid_search`.

Important examples of supported query shapes:

- direct lookup: `肉球森林`
- ambiguous lookup plus category: `寵物公園`
- landmark search: `青埔咖啡廳`
- address search: `中壢區 咖啡廳`
- feature search: `可落地的咖啡廳`
- recommendation search: `評價好的咖啡廳`
- open-now or time-window search: `現在有開的`, `晚上有開的咖啡廳`
- travel-time search: `步行15分鐘的公園`

The nearby endpoint is intentionally simpler. It does not use the LLM search planner. It validates coordinates, expands the frontend category when present, runs a MongoDB geospatial query, and returns distance-prioritized results.

Recommendation quality comes from two stages:

1. Property creation stores AI-enriched metadata such as pet features and AI rating.
2. Runtime search reuses those stored fields to filter and rank results.

That means search quality depends on both ingestion-time enrichment and query-time interpretation.

## Related Agent Docs

- `docs/search/architecture.md`
- `docs/search/workflow-optimization.md`
- `docs/search/workflow-nearby.md`
