# Opportunity Stage API QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

Close the Phase 3 stage-movement API gap by exposing deterministic Mission Control endpoints for opportunity stage moves and stage-history readback.

## Changes

- Added Mission Control stage-move request/response models.
- Added stage-history response model.
- Added `POST /mission-control/opportunities/{opportunity_id}/stage`.
- Added `GET /mission-control/opportunities/{opportunity_id}/stage-history`.
- Added service methods that call the existing configured-stage `OpportunityService.advance_stage` path, preserving current validation rules and stage-history persistence.
- Added API coverage for successful forward movement and rejected backward movement.

## TDD Evidence

The new stage API tests were written before implementation and initially failed with 404 because the endpoints did not exist. After implementation, the focused tests passed.

## Verification

Captured in `test-output.txt`.

Commands/results:

- Focused new stage API tests: 2 passed
- Mission Control + opportunity repository/schema regression tests: 41 passed
- `git diff --check`: passed

## Risks / Notes

- This slice exposes stage movement through Mission Control API but does not yet add the frontend pipeline controls.
- The endpoint relies on the existing configured-stage service rules: no backward moves and no moves out of terminal stages.
- Pipeline config admin/remap behavior remains a separate Phase 3 gap.

## Remaining Work

1. Wire Mission Control frontend pipeline controls to the stage API.
2. Add stage-history display and stage-age/card-count UI.
3. Add pipeline config admin/remap behavior if we need operator-editable pipeline stages.
