# Diff Summary

## Added

- `app/models/source_runs.py`: Trigger lifecycle request fields and Mission Control summary response schemas for source runs, artifacts, and latest morning brief.
- `app/db/source_runs.py`: tenant/environment-scoped in-memory idempotency indexes for nightly source-pull responses and morning briefs.
- `tests/services/test_nightly_lead_machine_service.py`: service coverage for nightly and morning-brief idempotency, warning-count de-duplication, manifests, tenant scoping, no-live rejection, failed manifests, default fixture manifests, and lane separation.
- `tests/api/test_nightly_lead_machine.py`: runtime/Mission Control endpoint coverage for lifecycle fields, idempotency, metadata minimization, auth checks, no-live rejection, and unknown-field validation.

## Modified

- `app/services/nightly_lead_machine_service.py`: replays repeated `idempotency_key` requests per `business_id`/`environment`, avoids manifest warning double-counting, and builds sanitized Mission Control summaries without arbitrary metadata echo.
- `app/api/mission_control.py`: returns sanitized summary models for latest morning brief and source-runs while preserving lane/count/status/source information.
- `app/models/source_runs.py`: `NightlySourcePullRequest` and `MorningBriefRequest` accept optional `run_id`, `command_id`, `idempotency_key`, and `trigger_run_id` while keeping `extra="forbid"`; nightly responses expose `duplicate`/`replayed` flags.
- `app/db/source_runs.py`: manifest warnings are de-duplicated when completing/failing runs and idempotency state is cleared on repository reset.
- `docs/qc/2026-05-14/nightly-lead-machine/`: refreshed QC report and exact test outputs.

## Boundary

This slice intentionally does not scrape or call Harris County, HCAD, HCTax, land records, providers, or Slack. Source pull input is supplied manifests or zero-count fixture defaults only.
