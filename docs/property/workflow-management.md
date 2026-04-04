# Property Management

## Scope

This document covers post-creation property management flows.

## When To Read This Doc

Read this document when:

- changing property mutation endpoints
- adjusting soft-delete or restore behavior
- updating audit behavior for property management

Read `docs/property/architecture.md` when you need the broader property-layer structure.

## Entry Points

- Patch manual pet-feature overrides: `PATCH /property/{property_id}/pet-features`
- Renew an existing property from upstream Places data: `POST /property/{property_id}/renew?mode=...`
- Soft delete a property: `DELETE /property/{property_id}`
- Restore a soft-deleted property: `POST /property/{property_id}/restore`
- List property audit logs: `GET /property/{property_id}/audit-logs`
- `application/property.py::PropertyService.update_pet_features`
- `application/property.py::PropertyService.renew_property`
- `application/property.py::PropertyService.soft_delete_property`
- `application/property.py::PropertyService.restore_property`
- `application/property.py::PropertyService.get_audit_logs`
- Supporting a repository path: `infrastructure/mongo/property.py`

## Rules

### Manual Pet-Feature Overrides

- Only provided fields should change.
- At least one override field must be present.
- Manual overrides become part of the effective pet features.
- Every override change must create an audit log entry.

### Soft Delete

- Soft-deleted properties remain in storage.
- Soft-deleted properties are excluded from normal search and detail APIs.
- Deleting an already deleted property should fail.

### Renew

- Renew targets an existing property by `property_id`.
- `basic` mode refreshes from Places Text Search Enterprise and Atmosphere and then Places Details Enterprise and Atmosphere.
- `details` mode refreshes only from Places Details Enterprise and Atmosphere using the existing raw source snapshot.
- Renew must not silently switch the property to a different resolved `place_id`.
- Renew should preserve manual overrides through the sync path.
- Renew uses the same sync audit behavior when a property entity is actually refreshed.

### Restore

- Restore should only succeed for soft-deleted properties.
- Restored properties become visible to normal APIs again.
- Restore must create an audit log entry.

### Audit Logs

- Audit history should include create, sync, pet-feature override, softly delete, and restore actions.
- Audit queries should validate that the target property exists.

- Property management actions are business logic and belong in `application/`.
- Route modules should stay thin and delegate behavior to `PropertyService`.
- Any change that affects property mutation behavior should keep audit behavior aligned in the same change.

## Validation

- Keep unit tests stable for mutation and audit behavior.
- If property mutation semantics change, update related fixtures, stubs, and doubles in the same change.
- If the change affects shared property behavior, run the relevant full unit suite before finishing.

## Related Files

- `interface/api/routes/v1/property.py`
- `application/property.py`
- `infrastructure/mongo/property.py`
- `interface/api/schemas/property.py`
- `tests/unit/application`
