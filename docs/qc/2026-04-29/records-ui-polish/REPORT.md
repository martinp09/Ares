# QC Report: Records UI Polish

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Repo: `martinp09/Ares`

## Scope

Polished the Mission Control Records workspace after the canonical CRM Records registry landed. This slice is intentionally read-only: no fake promote/suppress/import buttons before the Records command API exists.

## Changes

- Added Records operator tabs:
  - All
  - Needs Skip Trace
  - Marketable
  - Suppressed
  - Promoted
  - Incomplete
- Expanded KPI cards:
  - total records
  - needs skip trace
  - marketable / active
  - no phone
  - promoted
  - open tasks
- Added record badges for:
  - record type
  - source
  - contactability
  - data quality
  - promotion state
- Added explicit read-only inventory copy for non-promoted records so the UI does not imply write actions exist yet.
- Updated Records page tests for tabs, filters, badges, and absence of fake write actions.
- Updated `CONTEXT.md` and `memory.md`.

## Verification

Captured in `test-output.txt`.

Passed:

- `git diff --check`
- `npm --prefix apps/mission-control run test -- --run src/pages/RecordsPage.test.tsx`
  - `1 file passed / 2 tests passed`
- `npm --prefix apps/mission-control run test -- --run src/pages/RecordsPage.test.tsx src/pages/DashboardPage.test.tsx`
  - `2 files passed / 4 tests passed`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest tests/api/test_mission_control.py -q`
  - `30 passed`

## Notes / Risks

- The UI tabs are client-side filters over the current Records payload. Saved views are intentionally deferred until filter semantics are persisted through API state.
- Write actions remain deferred to the next slice: Records action API / promotion path.
