# User Architecture

## Scope

This document describes the structure, responsibilities, and design constraints of the user identity and authentication feature.

Read `docs/user/guide-auth-sequence.md` when you want a human-oriented walkthrough with diagrams before reading implementation details.

## When To Read This Doc

Read this document when:

- changing token structure, session invalidation, or auth dependency wiring
- deciding where identity verification and session lifecycle logic should live
- reviewing whether auth-related changes respect layer boundaries
- changing account deletion or restoration behavior that interacts with authentication

Read `docs/user/workflow-account-lifecycle.md` when you need execution rules, lifecycle constraints, or validation requirements for changing user flows.

## Entry Points

- Basic registration: `POST /api/v1/user/register`
- Apple login: `POST /api/v1/user/auth/apple`
- Refresh auth session: `POST /api/v1/user/auth/refresh`
- Logout current session: `POST /api/v1/user/auth/logout`
- Current user auth status: `GET /api/v1/user/me`
- Auth dependency wiring: `interface/api/dependencies/user.py`
- Auth session service: `application/auth_session.py`
- Apple auth service: `application/apple_auth.py`
- Backend token implementation: `infrastructure/auth/tokens.py`
- Apple token verifier: `infrastructure/apple/auth.py`
- User persistence: `infrastructure/mongo/user.py`

## Responsibilities

### Application Layer

- Own user registration, Apple-login business flow, and session lifecycle decisions.
- Decide how persisted user state participates in authentication validity.
- Keep user and auth policy out of transport-specific layers.

### Interface Layer

- Accept HTTP credentials and request payloads.
- Map validated bearer claims and resolved users into request dependencies.
- Translate application and auth failures into API-facing error responses.

### External Identity and Token Infrastructure

- Verify Apple-issued identity tokens against Apple keys.
- Sign and verify backend-issued access and refresh tokens.
- Keep provider-specific verification and token mechanics out of application orchestration.

### Persistence Layer

- Persist user records and session-backed state such as `session_version` and `refresh_token_hash`.
- Expose repository methods for lookup, mutation, soft delete, and restore.
- Avoid moving authentication policy into MongoDB adapters.

## Design Constraints

### Identity Sources

- `basic` users are created by `POST /api/v1/user/register`.
- `apple` users are resolved or created by `POST /api/v1/user/auth/apple`.
- After login or registration succeeds, normal authenticated traffic must use backend-issued bearer tokens, not the original login credential.

### Apple Identity Verification

- Apple login must verify the Apple `identity_token` against Apple JWKS before user creation or lookup completes.
- The verified Apple `sub` is the canonical external identity for Apple-backed users.
- Apple verification mechanics belong in infrastructure; binding and lifecycle decisions belong in application.

### Backend Auth Session

- After registration or Apple login, the backend starts its own auth session and returns `access_token`, `refresh_token`, and the latest user snapshot.
- Access and refresh tokens are backend-signed with different TTLs and carry user identity plus session-version claims.
- The token format is an implementation detail of `infrastructure/auth/tokens.py`, but session semantics are an application concern.

### Request Authentication

- `get_current_user` and `get_optional_current_user` should remain interface-facing entry points for bearer resolution.
- Token verification alone is insufficient; authenticated user resolution also depends on persisted user state.
- Auth validity must continue to consider user existence, soft-delete state, `source`, and `session_version`.

### Session invalidation

- Starting a new auth session increments the stored `session_version`.
- Refresh does not increment `session_version`; it rotates only the stored `refresh_token_hash`.
- Logout clears `refresh_token_hash` and increments `session_version`.
- Because access tokens carry `session_version`, logout invalidates older access tokens without a separate access-token blacklist.
- Soft-deleting a user also causes existing tokens to fail because the resolved user is treated as invalid credentials.

## Related Files

- `docs/user/guide-auth-sequence.md`
- `docs/user/workflow-account-lifecycle.md`
- `interface/api/routes/v1/user.py`
- `interface/api/dependencies/user.py`
- `application/user.py`
- `application/apple_auth.py`
- `application/auth_session.py`
- `infrastructure/auth/tokens.py`
- `infrastructure/apple/auth.py`
- `infrastructure/mongo/user.py`
- `domain/entities/user.py`
- `domain/repositories/user.py`
