# Pipeline Stage UI Diff Summary

## Frontend API

- `apps/mission-control/src/lib/api.ts`
  - Added opportunity stage move request/response types.
  - Added stage-history response payload mapping.
  - Added `moveOpportunityStage(...)` API client method wired to `POST /mission-control/opportunities/{opportunity_id}/stage`.

- `apps/mission-control/src/lib/api.test.ts`
  - Added API client coverage proving the stage move method posts the expected endpoint/body and maps the response.

## Frontend UI

- `apps/mission-control/src/pages/PipelinePage.tsx`
  - Added a small operator form for moving an opportunity to a target stage.
  - Keeps submit disabled until an opportunity ID is provided.
  - Displays action status after submit.

- `apps/mission-control/src/pages/PipelinePage.test.tsx`
  - Added focused tests for submitting stage movement and disabled state.

- `apps/mission-control/src/App.tsx`
  - Added pipeline action state.
  - Wired Pipeline page submit to the real API client.
  - Refreshes dashboard data after stage movement.

## Docs/QC

- `docs/qc/2026-04-29/pipeline-stage-ui/`
  - Added QC report, diff summary, test output, and diff snapshots.
- `CONTEXT.md`, `memory.md`
  - Updated open work and changelog.
