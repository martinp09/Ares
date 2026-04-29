# QC Report: Records Action API

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Repo: `martinp09/Ares`

## Scope

Implemented the backend command path for canonical Mission Control CRM Records after the Records UI polish slice.

## Changes

- Added Mission Control Records action request/response models.
- Added API endpoints for:
  - `POST /mission-control/records/import`
  - `POST /mission-control/records/{record_id}/status`
  - `POST /mission-control/records/{record_id}/suppress`
  - `POST /mission-control/records/{record_id}/promote`
- Added service methods to import canonical records, write source memberships, write status history, suppress records, and promote records into opportunities.
- Added promotion validation requiring exactly one of `lead_id` or `contact_id`.
- Hardened Supabase promotion insertion to return an existing promotion for the same record/opportunity instead of duplicating the unique key.
- Added regression tests for import -> status -> suppress -> promote, repeated promotion idempotency, and invalid promotion identity payloads.
- Updated `CONTEXT.md` and `memory.md` to reflect the completed action API slice and next work.

## Verification

Captured in `test-output.txt`:

- `git diff --check` — passed
- `uv run pytest tests/api/test_mission_control.py tests/db/test_crm_records_repository.py tests/db/test_crm_records_schema.py -q` — `35 passed`
- `uv run pytest -q` — `595 passed, 6 warnings`
- `uv run python -m compileall app` — passed
- `npm --prefix apps/mission-control run test -- --run src/pages/RecordsPage.test.tsx` — `2 passed`
- `npm --prefix apps/mission-control run typecheck` — passed

## Known Warnings

The full backend suite still reports six pre-existing FastAPI/AnyIO deprecation warnings around `HTTP_422_UNPROCESSABLE_ENTITY`. They are not introduced by this slice.

## Remaining Gaps

- Live Supabase runtime smoke has not been run in this slice.
- Mission Control UI buttons are still intentionally not wired to these endpoints.
- Configurable pipelines/stage history remains the next implementation-plan slice.
- Saved views should follow after filters/API state stabilize.
