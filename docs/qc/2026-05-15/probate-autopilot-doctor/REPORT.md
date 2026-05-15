# QC Report — Probate Autopilot Doctor

## Scope

Fourth no-send execution slice for the Harris + Montgomery probate autopilot PRD.

This slice adds a small watchdog/operator-health CLI that reads the durable source-run ledger and emits a JSON health report for unattended runs.

## Implemented

- Added `scripts/probate_autopilot_doctor.py`:
  - Reads a configured source-run state file (`LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` equivalent).
  - Loads the latest morning brief for a business/environment.
  - Emits JSON with:
    - overall SLA status;
    - no-send safety status;
    - anomaly count and top anomalies;
    - enrichment backlog;
    - operator next actions;
    - warning/source-run counts.
  - Supports `--fail-on-blocked` so cron/watchdog wrappers can treat blocked SLA as a non-zero exit without sending/provider side effects.
- Added tests for:
  - blocked missing-county SLA report;
  - `--fail-on-blocked` exit code;
  - empty/no-data ledger behavior.

## Safety posture

No live county scraping was added.

No provider side effects were added:

- no HubSpot writes;
- no Instantly enrollment/activation/send;
- no SMS/Vapi/direct mail;
- no paid skiptrace;
- no provider/webhook call.

The doctor script is read-only against the local source-run ledger.

## Verification

Captured in `test-output.txt`:

- `python -m pytest tests/scripts/test_probate_autopilot_doctor.py tests/scripts/test_probate_source_file_payload.py tests/services/test_probate_source_file_service.py tests/services/test_nightly_lead_machine_service.py tests/api/test_nightly_lead_machine.py tests/api/test_trigger_contract_files.py tests/api/test_runtime_config_contract.py tests/services/test_harris_probate_intake_service.py tests/services/test_probate_write_path_service.py tests/services/test_tax_overlay_service.py -q`
  - Result: `64 passed`
- `npm --prefix trigger run typecheck`
  - Result: pass
- `git diff --check`
  - Result: clean

## Remaining gates

- Wire this doctor into an actual host watchdog/cron only after choosing where alerts should be delivered.
- Real Harris/Montgomery source adapters remain separate no-send source-provider work.
- HubSpot mirror, Instantly/SMS/Vapi, paid skiptrace, and direct mail remain separate approval gates.
