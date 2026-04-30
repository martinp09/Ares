# Pipeline Stage UI QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

Wire Mission Control Pipeline UI controls to the Phase 3 opportunity stage movement API.

## What Changed

- Added Pipeline page stage movement form with:
  - opportunity ID input
  - configured target-stage selector derived from dashboard pipeline summaries
  - move reason input
  - disabled submit until an opportunity ID is present
  - inline action status feedback
- Added frontend API client support for `POST /mission-control/opportunities/{opportunity_id}/stage`.
- Added response mapping for updated opportunity, latest stage event, and stage history.
- Wired `App.tsx` to call the real API, refresh dashboard pipeline summaries, and report success/error state.
- Added focused frontend tests for the Pipeline page and API client.

## Verification

Captured in `test-output.txt`:

- RED evidence: focused Pipeline page test failed before controls existed.
- `npm run typecheck` passed.
- `npm test -- --run src/lib/api.test.ts src/pages/PipelinePage.test.tsx src/pages/RecordsPage.test.tsx` passed.
- `npm run build` passed.
- Backend stage API regression tests passed.

## Risks / Notes

- The Pipeline UI is intentionally minimal: operators must enter an opportunity ID manually until a richer opportunity-list/detail surface exists.
- The form only exposes stages already present in the dashboard pipeline summary; a later admin/config slice should expose all configured stages even when count is zero.
