# Parking Pet API

Parking Pet API is a FastAPI backend for discovering, enriching, and managing pet-friendly places.

The project combines:

- Google Places data ingestion
- AI-based property enrichment
- natural-language search intent parsing
- MongoDB persistence and geospatial querying
- manual pet-feature overrides and audit logging

This README is intended to be a practical project reference for future contributors and coding agents.

## What This Service Does

The API supports two main workflows:

1. Search pet-friendly properties using natural-language queries such as "pet-friendly cafe near Taipei 101 with outdoor seating".
2. Create or sync property records from Google Places, enrich them with AI-generated pet-related analysis, and store them for later search.

It also supports user profile basics, favorite properties, soft deletion, restoration, and audit history.

## Tech Stack

- Python `>=3.14,<4.0.0`
- FastAPI
- Uvicorn
- MongoDB via Motor
- Pydantic v2
- LangChain / LangGraph
- Google Gemini / Vertex AI
- Google Places API
- Poetry
- Pytest

## Architecture Overview

The codebase follows a layered structure:

- `interface/`: FastAPI routes, request dependencies, response schemas, exception handling
- `application/`: orchestration and use-case services
- `domain/`: entities, repository interfaces, and domain contracts
- `infrastructure/`: MongoDB repositories, Google integrations, prompts, logging, runtime wiring
- `tests/`: unit tests for application logic, adapters, and persistence behavior
- `docs/`: additional design notes

High-level request flow:

1. A request enters FastAPI under `/api/v1`.
2. The route resolves dependencies and calls an application service.
3. The service delegates to repositories and enrichment providers.
4. Infrastructure modules talk to MongoDB, Google Places, and Google AI services.
5. Results are returned as API response models.

## Key Modules

### API entrypoint

- `main.py`
- `interface/api/entrypoint.py`

`main.py` creates the FastAPI app and starts Uvicorn on port `8000`.

### Property API

- `interface/api/routes/v1/property.py`
- `application/property.py`

This is the core product surface. It handles:

- semantic property search
- nearby property search
- property detail lookup
- property creation and sync
- manual pet-feature overrides
- soft delete / restore
- property audit logs

### User API

- `interface/api/routes/v1/user.py`
- `application/user.py`

This covers:

- basic user registration by name
- current user lookup via `x-user-id`
- profile updates
- favorite property management

### Search interpretation

- `infrastructure/search/pipeline.py`
- `infrastructure/search/prompts.py`
- `application/property_search/rules.py`
- `domain/entities/search.py`
- `domain/services/property_enrichment.py`

Natural-language search queries are converted into a structured `SearchPlan`, which determines whether the request should use:

- semantic retrieval through MongoDB filters, or
- keyword fallback search

The search planner extracts signals such as:

- category intent
- location intent
- pet-feature preferences
- recommendation / quality hints
- open-now preference

### Property persistence

- `infrastructure/mongo/property.py`
- `domain/entities/property.py`

Stored properties include:

- normalized place information
- AI analysis
- manual overrides
- computed effective pet features
- opening-hour segments for runtime open-now checks
- geospatial `location` data for MongoDB geo queries

## Search Model

The search flow is closer to AI-assisted structured filtering than full-text search.

At a high level:

1. Parse the user query into a `SearchPlan`.
2. Build a MongoDB query from structured intent.
3. Optionally apply geospatial context from user or map coordinates.
4. Query MongoDB.
5. Re-rank the results in the application layer.
6. Fall back to regex keyword search when the plan chooses keyword mode or uses semantic fallback.

Important ranking inputs in `PropertyService`:

- AI rating
- pet-feature density
- query-requested pet-feature matches
- distance score
- type match bonus
- open-now bonus

For more detail, see `docs/search/architecture.md`.

## Main Collections

The current dependency wiring uses these MongoDB collections:

- `property_v2`
- `place_raw_data`
- `property_audit_logs`
- `user`

## Environment Variables

Settings are loaded from `.env` using Pydantic nested environment keys.

Current settings model requires:

- Mongo settings under `mongo__*`
- Google settings under `google__*`

Minimal example:

```env
MONGO__PROTOCOL=mongodb
MONGO__HOST=localhost
MONGO__PORT=27017
MONGO__USERNAME=user
MONGO__PASSWORD=pass
MONGO__DB_NAME=parking_pet

GOOGLE__PROJECT_ID=your-gcp-project-id
GOOGLE__LOCATION=asia-east1
GOOGLE__SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
GOOGLE__PLACE_API_KEY=your-google-places-api-key
```

Notes:

- `.env.example` currently only includes Mongo placeholders and is incomplete relative to the actual settings model.
- The application will need valid Google credentials to use enrichment and semantic search features backed by Gemini / Vertex AI.

## Running the Project

Install dependencies with Poetry:

```bash
poetry install
```

Start the API:

```bash
poetry run python main.py
```

The app listens on:

- `http://0.0.0.0:8000`

If you prefer the existing helper target:

```bash
make run-server
```

Stop the background server:

```bash
make stop-server
```

## Running Tests

Run the test suite:

```bash
make test
```

Or directly:

```bash
poetry run pytest tests
```

Lint and format:

```bash
make lint
```

## Authentication Model

This project currently uses bearer-token-based user authentication:

- users authenticate through either `POST /api/v1/user/register` or `POST /api/v1/user/auth/apple`
- Apple `identity_token` is used only during Apple login and is not the bearer token for normal API calls
- successful login or registration returns a backend-issued `access_token` and `refresh_token`
- authenticated endpoints expect `Authorization: Bearer <access-token>`
- `GET /api/v1/user/me` verifies the bearer token, then resolves the current user from MongoDB
- bearer-token validation also checks the persisted user `source` and `session_version`
- `POST /api/v1/user/auth/refresh` rotates the refresh token and returns a new auth session
- `POST /api/v1/user/auth/logout` revokes the session by clearing the stored refresh-token hash and bumping the session version
- soft-deleted users are treated as invalid credentials
- some property mutations allow anonymous actors, while others require an authenticated user

This is closer to application-level identity wiring than a production auth system.

For the current user lifecycle and Apple Login behavior, read `docs/user/workflow-account-lifecycle.md`.

## Important Domain Concepts

### PropertyEntity

`PropertyEntity` is the central record. In addition to persisted fields, it derives:

- `location`
- `op_segments`
- `rating`
- `effective_pet_features`
- `is_open`
- `category`
- `types`

### AI analysis vs manual overrides

The project intentionally separates:

- AI-inferred pet-related features
- manual override values entered later

The API exposes the merged effective view through `effective_pet_features`.

### Soft deletion

Properties are not hard-deleted by default. They are marked with:

- `is_deleted`
- `deleted_at`
- `deleted_by`

Normal search and detail endpoints exclude soft-deleted records.

### Audit logs

Property mutations generate audit entries for actions such as:

- create
- sync
- pet-feature override
- soft delete
- restore

## Current API Surface

Main routes under `/api/v1`:

### Property routes

- `GET /property`
- `GET /property/nearby`
- `GET /property/{property_id}`
- `POST /property`
- `PATCH /property/{property_id}/pet-features`
- `DELETE /property/{property_id}`
- `POST /property/{property_id}/restore`
- `GET /property/{property_id}/audit-logs`

### User routes

- `POST /user/auth/apple`
- `POST /user/auth/refresh`
- `POST /user/auth/logout`
- `POST /user/register`
- `GET /user/profile`
- `PATCH /user/profile`
- `GET /user/me`
- `PUT /user/favorite/{property_id}`
- `GET /user/favorite/{property_id}`
- `GET /user/favorite`
- `GET /user/search-history`
- `GET /user/property-notes`
- `DELETE /user`

## Known Observations

- The project metadata references `README.md`; this file exists to satisfy that expectation and provide a stable orientation point.
- `MongoDBClient` is instantiated through FastAPI dependencies, so it currently behaves more like a lightweight provider than a true process-wide singleton.
- `main.py` starts Uvicorn with `workers=5`, which is useful to know when debugging runtime behavior.
- Search and enrichment behavior depends on external Google services, so some flows are not fully runnable with MongoDB alone.

## Recommended Reading Order

If you are new to the project, read files in this order:

1. `README.md`
2. `docs/search/architecture.md`
3. `interface/api/routes/v1/property.py`
4. `application/property.py`
5. `domain/entities/property.py`
6. `infrastructure/search/pipeline.py`
7. `infrastructure/mongo/property.py`

## Future README Improvements

Useful follow-ups for this file:

- add a local development section for seeding sample data
- document the Google Places and Vertex AI permissions required
- add example request / response payloads
- add architecture diagrams
- document collection indexes, especially geospatial indexes
