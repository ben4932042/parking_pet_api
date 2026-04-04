# Logging Workflow

## Scope

This document defines the request/event logging structure used by the API.

Read this document when:

- changing request logging behavior
- adding or renaming API event logs
- adjusting `request_id`, `route_name`, or query/body summaries
- deciding where a new log should be emitted

## Design Split

### HTTP Access Log

- Event name: `http_access`
- Emitted from `interface/api/middlewares/logging.py`
- Level: `DEBUG`
- Purpose: one log per HTTP request with request/response summary

### Request Failure Log

- Event name: `request_failed`
- Emitted from `interface/api/exceptions/exception_handlers.py`
- Level: `ERROR`
- Purpose: one log per handled API failure with status/error context

### Domain Event Log

- Emitted from route/application flow after a business action succeeds or fails
- Purpose: user trace and product-action visibility

## Request ID Rule

- Prefer Cloudflare `cf-ray` as `request_id`
- If `cf-ray` is absent, generate a fallback request id
- Always record `request_id_source` with value `cf-ray` or `generated`

## Route Name Rule

- Include `route_name` in `http_access`
- Use stable route names via FastAPI route `name=...`
- Prefer `verb_resource[_qualifier]` naming, such as:
  - `login_with_apple`
  - `refresh_auth_token`
  - `update_user_profile`
  - `list_properties`
  - `list_nearby_properties`
  - `get_property_detail`
  - `upsert_property_note`
  - `list_property_notes`

## Query Summary Rule

- Do not rely on raw query string in the main access log
- Store a parsed `query_summary` object instead
- Domain events may add endpoint-specific summaries such as `keyword`, `filter_keys`, or `result_count`

## Event List

- `http_access`
- `request_failed`
- `auth_registered`
- `auth_login_succeeded`
- `auth_login_failed`
- `auth_token_refreshed`
- `auth_refresh_failed`
- `auth_logout_succeeded`
- `auth_invalid_token`
- `auth_session_mismatch`
- `user_profile_updated`
- `user_favorite_added`
- `user_favorite_removed`
- `user_favorite_list_viewed`
- `property_search_executed`
- `property_nearby_search_executed`
- `property_viewed`
- `user_property_note_upserted`
- `user_property_notes_viewed`

## Placement Rules

- `http_access`: middleware only
- `request_failed`: exception handler only
- auth/user/property/note trace events: emit close to the completed use case, using the shared logging helper

## Related Files

- `interface/api/middlewares/logging.py`
- `interface/api/exceptions/exception_handlers.py`
- `interface/api/logging_utils.py`
- `interface/api/routes/v1/user.py`
- `interface/api/routes/v1/property.py`
