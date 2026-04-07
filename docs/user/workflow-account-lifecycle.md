# User Account Lifecycle Workflow

## Scope

This document covers the current user account lifecycle, including guest auth, Apple login, Apple linking, authenticated profile flows, and account deletion or restoration behavior.

## When To Read This Doc

Read this document when:

- changing guest-auth behavior
- changing Apple Login behavior
- changing header-based authentication behavior
- changing profile, favorite, search-history, or note flows that depend on the current user
- changing account deletion or restoration behavior

Read `docs/user/architecture.md` first when you need a structure-oriented explanation of the current auth design, token roles, or layer boundaries.

Read `docs/user/guide-auth-sequence.md` when you want a diagram-first walkthrough of the auth and session flow.

Read `docs/property/workflow-favorite.md` when the change is specifically about favorite-property behavior.

## Entry Points

- Guest auth: `POST /api/v1/user/auth/guest`
- Apple login: `POST /api/v1/user/auth/apple`
- Apple link for guest users: `POST /api/v1/user/auth/apple/link`
- Refresh auth session: `POST /api/v1/user/auth/refresh`
- Logout current session: `POST /api/v1/user/auth/logout`
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
- Apple `identity_token` is only used during Apple login. Normal authenticated API calls use backend-issued bearer tokens.
- `get_current_user` must reject requests with no bearer token, malformed bearer headers, unknown users, or soft-deleted users.
- `get_optional_current_user` may return `None` for anonymous, unknown, or soft-deleted users.
- Guest auth creates a new user with `source="guest"`.
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
- Successful guest auth, successful Apple login, and successful Apple linking all start an auth session and return:
  - `access_token`
  - `refresh_token`
  - the latest user snapshot
- Access and refresh tokens are backend-signed and include:
  - `sub` for the user id
  - `source` for the user source such as `guest` or `apple`
  - `type` for `access` or `refresh`
  - `sv` for `session_version`
  - `iss`, `iat`, and `exp`
- Authenticated user resolution must verify both token integrity and persisted user state:
  - signature
  - issuer
  - expiry
  - matching user id
  - matching `source`
  - matching `session_version`
  - user is not soft deleted
- Refreshing a session must also require the presented refresh token to match the stored `refresh_token_hash`.
- Starting a new session increments `session_version`.
- Logging out revokes the stored refresh token and increments `session_version`, which invalidates older access tokens.
- Account deletion is currently a soft delete on the user record only. It must not erase user-owned data.
- User soft deletion is represented by:
  - `is_deleted`
  - `deleted_at`
- Re-authenticating with the same Apple account restores the soft-deleted account by clearing `is_deleted` and `deleted_at`.

## Current Lifecycle

### 1. Guest auth

- Client calls `POST /api/v1/user/auth/guest` with `name` and optional `pet_name`.
- Backend creates a new user document.
- Backend starts an auth session for the newly created user.
- The response returns the created user payload together with `access_token` and `refresh_token`.

### 2. Apple login

- Client calls `POST /api/v1/user/auth/apple`.
- Backend verifies the Apple `identity_token`.
- Backend looks up a user by Apple `sub`, then optionally by incoming `user_identifier`.
- If a matching active user exists, backend returns it.
- If a matching deleted user exists, backend restores it and returns it.
- If no matching user exists and `name` is missing, backend returns `422`.
- If no matching user exists and required fields are present, backend creates a new Apple user and returns it.
- Backend starts an auth session and returns backend-issued `access_token` and `refresh_token`.

### 3. Guest links Apple

- Client calls `POST /api/v1/user/auth/apple/link` with `Authorization: Bearer <access-token>`.
- Backend requires the authenticated user to still be a guest user.
- Backend verifies the Apple `identity_token`.
- Backend rejects the request if the verified Apple identity is already linked to another user.
- Backend upgrades the same guest user record in place to `source="apple"` and stores the verified Apple `sub`.
- Backend starts a fresh auth session and returns backend-issued `access_token` and `refresh_token`.

### 4. Authenticated requests

- Client sends `Authorization: Bearer <access-token>` on authenticated routes.
- Backend verifies the token signature, issuer, expiry, token type, and claims.
- Backend resolves the current user from MongoDB.
- Backend rejects the request unless the stored user still matches the token `source` and `session_version`.
- Soft-deleted users are treated as invalid credentials.

### 5. Refresh session

- Client calls `POST /api/v1/user/auth/refresh` with the current `refresh_token`.
- Backend verifies the refresh token.
- Backend loads the user and rejects the request if the user is missing, deleted, source-mismatched, session-version-mismatched, or the stored `refresh_token_hash` does not match the presented token.
- Backend rotates the refresh token by storing the hash of a newly issued refresh token.
- Backend returns a new `access_token`, a new `refresh_token`, and the latest user snapshot.

### 6. Logout

- Client calls `POST /api/v1/user/auth/logout` with `Authorization: Bearer <access-token>`.
- Backend clears the stored `refresh_token_hash`.
- Backend increments `session_version`.
- Existing refresh tokens become unusable.
- Existing access tokens also stop working because the persisted `session_version` no longer matches the token claims.

### 7. User-owned interaction data

- Favorite property ids are stored on the user record in `favorite_property_ids`.
- Search history is stored on the user record in `recent_searches`.
- Property notes are stored on the user record in `property_notes`.
- Property-facing note workflows may still compose property overview data before returning API responses.
- Search feedback is stored separately and linked by user id.

### 8. Account deletion

- Client calls `DELETE /api/v1/user`.
- Backend marks the current user as deleted.
- The user record remains in storage.
- Existing access tokens stop working after deletion because the deleted user is treated as invalid credentials.
- Apple login with the same Apple account restores the same user later.

## Validation

- Keep unit tests stable for:
  - guest auth
  - guest-to-Apple linking
  - Apple login success and failure cases
  - auth session creation
  - refresh-token rotation
  - logout session revocation
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
- `application/auth_session.py`
- `domain/entities/user.py`
- `domain/repositories/user.py`
- `infrastructure/auth/tokens.py`
- `infrastructure/mongo/user.py`
- `infrastructure/apple/auth.py`
- `interface/api/schemas/user.py`
- `tests/unit/application/test_user_service.py`
- `tests/unit/application/test_apple_auth.py`
- `tests/unit/adapters/fastapi/test_user.py`
- `tests/unit/adapters/fastapi/test_user_auth.py`
- `tests/unit/infrastructure/test_mongo_user.py`
- `tests/unit/infrastructure/test_apple_identity_verifier.py`
