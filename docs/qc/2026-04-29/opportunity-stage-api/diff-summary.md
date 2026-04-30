# Opportunity Stage API Diff Summary

## Backend API

- `app/api/mission_control.py`
  - Added `POST /mission-control/opportunities/{opportunity_id}/stage` for moving an opportunity to a configured stage.
  - Added `GET /mission-control/opportunities/{opportunity_id}/stage-history` for readback of persisted stage movement events.

## Models

- `app/models/mission_control.py`
  - Added `MissionControlOpportunityStageMoveRequest`.
  - Added `MissionControlOpportunityStageMoveResponse`.
  - Added `MissionControlOpportunityStageHistoryResponse`.

## Service

- `app/services/mission_control_service.py`
  - Added `move_opportunity_stage` wrapper around `OpportunityService.advance_stage`.
  - Added `get_opportunity_stage_history` readback wrapper.

## Tests

- `tests/api/test_mission_control.py`
  - Added forward stage movement API regression.
  - Added backward movement rejection regression.

## QC Artifacts

- `docs/qc/2026-04-29/opportunity-stage-api/REPORT.md`
- `docs/qc/2026-04-29/opportunity-stage-api/diff-summary.md`
- `docs/qc/2026-04-29/opportunity-stage-api/test-output.txt`
