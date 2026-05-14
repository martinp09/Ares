# Diff Summary

## App/code changes

- `app/core/config.py`
  - Added global `provider_live_sends_enabled` setting with `PROVIDER_LIVE_SENDS_ENABLED` alias, default false.
- `.env.example`
  - Documented `PROVIDER_LIVE_SENDS_ENABLED=false` next to HubSpot live-write flags.
- `app/providers/hubspot.py`
  - Added `list_property_groups(object_type)`.
  - Added `create_pipeline_stage(object_type, pipeline_id, payload)`.
  - Updated retry-delay parsing to honor sanitized `Retry-After` headers case-insensitively, including lowercase `retry-after`.
- `app/services/hubspot_mirror_service.py`
  - Added reusable customization payload builder.
  - Added `apply_customization(operator_approval=False)` with strict preflight gates.
  - Added idempotent create-missing-only logic for property groups, properties, pipeline, and stages.
  - Updated preview `live_write_enabled` to reflect both global and HubSpot-specific live gates.
- `app/models/mission_control.py`
  - Added HubSpot customization apply request/response schemas.
- `app/api/mission_control.py`
  - Added `POST /mission-control/providers/hubspot/customization/apply` endpoint.

## Test changes

- `tests/conftest.py`
  - Forces `PROVIDER_LIVE_SENDS_ENABLED=false` during tests.
- `tests/services/test_hubspot_mirror_service.py`
  - Added fake HubSpot customization client.
  - Added gate rejection tests for operator approval, global gate, HubSpot gate, and missing token.
  - Added fake-client success test for creating missing groups/properties/pipeline.
  - Added fake-client idempotency test for existing property group/property/pipeline/stage path.
  - Preserved preview no-provider-call tests.
- `tests/api/test_hubspot_mirror.py`
  - Added apply endpoint gate rejection tests.
  - Updated live-preview rejection test for the new global gate.
- `tests/providers/test_hubspot.py`
  - Added request-shape assertions for property groups and pipeline stages.
  - Added provider retry test proving lowercase `retry-after` is honored for delay while unsafe headers remain sanitized away.

## Documentation/QC changes

- `docs/qc/2026-05-14/hubspot-customization-apply/REPORT.md`
- `docs/qc/2026-05-14/hubspot-customization-apply/test-output.txt`
- `docs/qc/2026-05-14/hubspot-customization-apply/diff-summary.md`
- `CONTEXT.md`
- `memory.md`

## Secrets and live writes

- No secrets added.
- No real HubSpot writes/calls performed by this task.
- All write-path tests use fake/injected clients only.