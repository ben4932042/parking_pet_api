# User Account Lifecycle Workflow

## Scope

This document covers the current user account lifecycle, including registration, Apple login, authenticated profile flows, and account deletion or restoration behavior.

## When To Read This Doc

Read this document when:

- changing user registration behavior
- changing Apple Login behavior
- changing header-based authentication behavior
- changing profile, favorite, search-history, or note flows that depend on the current user
- changing account deletion or restoration behavior

Read `docs/property/workflow-favorite.md` when the change is specifically about favorite-property behavior.

## Entry Points

- Basic registration: `POST /api/v1/user/register`
- Apple login: `POST /api/v1/user/auth/apple`
- Current user auth status: `GET /api/v1/user/me`
- Profile read: `GET /api/v1/user/profile`
- Profile update: `PATCH /api/v1/user/profile`
- Favorite routes: `PUT /user/favorite/{property_id}`, `GET /user/favorite/{property_id}`, `GET /user/favorite`
- Search history: `GET /user/search-history`
- Property notes list: `GET /user/property-notes`
- Delete current user: `DELETE /api/v1/user`
- Route module: `interface/api/routes/v1/user.py`
- Auth dependency wiring: `interface/api/dependencies/user.py`
- User application service: `application/user.py`
- Apple auth application service: `application/apple_auth.py`
- Apple token verifier: `infrastructure/apple/auth.py`
- User repository contract: `domain/repositories/user.py`
- User repository implementation: `infrastructure/mongo/user.py`
- User entity and schemas:
  - `domain/entities/user.py`
  - `interface/api/schemas/user.py`

## Rules

- This project currently uses bearer-token authentication. Authenticated routes expect `Authorization: Bearer <access-token>`.
- `get_current_user` must reject requests with no bearer token, malformed bearer headers, unknown users, or soft-deleted users.
- `get_optional_current_user` may return `None` for anonymous, unknown, or soft-deleted users.
- Basic registration creates a new user with `source="basic"`.
- Apple login verifies the Apple identity token before any user lookup or creation.
- Apple identity token verification must validate:
  - the Apple signature against Apple JWKS
  - `iss`
  - `aud == APPLE__BUNDLE_ID`
  - token expiry
  - presence of `sub`
- Apple user binding uses the verified Apple `sub` as the primary external identifier. The flow may also check the incoming `user_identifier` for compatibility with older or partial bindings.
- If Apple login finds an existing active user, it returns that user.
- If Apple login finds a soft-deleted user, it restores that same user and returns it.
- If Apple login does not find a user and `name` is missing, it must return a validation error so the client can enter a supplement-information flow.
- If Apple login does not find a user and the required fields are present, it creates a new `source="apple"` user.
- Account deletion is currently a soft delete on the user record only. It must not erase user-owned data.
- User soft deletion is represented by:
  - `is_deleted`
  - `deleted_at`
- Re-authenticating with the same Apple account restores the soft-deleted account by clearing `is_deleted` and `deleted_at`.

## Current Lifecycle

### 1. Basic registration

- Client calls `POST /api/v1/user/register` with `name` and optional `pet_name`.
- Backend creates a new user document.
- The response returns the created user payload, including `_id`.

### 2. Apple login

- Client calls `POST /api/v1/user/auth/apple`.
- Backend verifies the Apple `identity_token`.
- Backend looks up a user by Apple `sub`, then optionally by incoming `user_identifier`.
- If a matching active user exists, backend returns it.
- If a matching deleted user exists, backend restores it and returns it.
- If no matching user exists and `name` is missing, backend returns `422`.
- If no matching user exists and required fields are present, backend creates a new Apple user and returns it.

### 3. Authenticated requests

- Client sends `Authorization: Bearer <access-token>` on authenticated routes.
- Backend resolves the current user from MongoDB.
- Soft-deleted users are treated as invalid credentials.

### 4. User-owned interaction data

- Favorite property ids are stored on the user record in `favorite_property_ids`.
- Search history is stored on the user record in `recent_searches`.
- Property notes are stored separately and joined at the route layer when needed.
- Search feedback is stored separately and linked by user id.

### 5. Account deletion

- Client calls `DELETE /api/v1/user`.
- Backend marks the current user as deleted.
- The user record remains in storage.
- Existing access tokens stop working after deletion because the deleted user is treated as invalid credentials.
- Apple login with the same Apple account restores the same user later.

## Validation

- Keep unit tests stable for:
  - basic registration
  - Apple login success and failure cases
  - deleted-user auth rejection
  - deleted Apple-user restoration
  - delete-account behavior
- If user repository contracts change, update all related stubs and mocks in the same change.
- If Apple verification rules change, update both application-level and infrastructure-level tests.
- If account deletion semantics change, verify both authentication behavior and relogin behavior.

## Related Files

- `interface/api/routes/v1/user.py`
- `interface/api/dependencies/user.py`
- `application/user.py`
- `application/apple_auth.py`
- `domain/entities/user.py`
- `domain/repositories/user.py`
- `infrastructure/mongo/user.py`
- `infrastructure/apple/auth.py`
- `interface/api/schemas/user.py`
- `tests/unit/application/test_user_service.py`
- `tests/unit/application/test_apple_auth.py`
- `tests/unit/adapters/fastapi/test_user.py`
- `tests/unit/adapters/fastapi/test_user_auth.py`
- `tests/unit/infrastructure/test_mongo_user.py`
- `tests/unit/infrastructure/test_apple_identity_verifier.py`
