# Records Bulk Actions QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

Add a bounded Records bulk-action UI using the existing real CRM command callbacks. Do not add a backend bulk endpoint for this slice.

## What Changed

- Added selected-record state to `RecordsPage`.
- Added per-row selection checkboxes plus a select-visible control.
- Added bulk action controls for selected visible records:
  - Mark marketable selected
  - Needs skip trace selected
  - Suppress selected
- Bulk actions fan out through the existing single-record status/suppress callbacks that `App.tsx` wires to the real CRM command API.
- Bulk buttons are disabled when no visible selected records exist or any record action is running.
- Saved-view/tab filtering remains layered through `visibleRecords`, so bulk actions only affect selected rows currently visible in the active saved view and tab.
- Promotion gating remains row-level and unchanged.
- Added focused Records page coverage for visible-only fanout, disabled states, and promotion gating preservation.

## Verification

Captured in `test-output.txt`:

- RED evidence: focused Records bulk test failed before row selection controls existed.
- `npm run typecheck` passed.
- `npm test -- --run src/pages/RecordsPage.test.tsx src/pages/PipelinePage.test.tsx src/lib/api.test.ts` passed: 16 tests.
- `npm run build` passed.
- `uv run pytest tests/api/test_mission_control.py::test_records_action_api_imports_updates_suppresses_and_promotes_records -q` passed.
- `git diff --check` passed.

## Risks / Notes

- Bulk actions intentionally fan out through existing single-record command callbacks. This preserves the real command path without adding a premature backend bulk API.
- Document an atomic backend bulk endpoint as future work only if operators need large-batch throughput or transaction semantics.
