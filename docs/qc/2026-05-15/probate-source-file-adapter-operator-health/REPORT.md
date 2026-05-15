# QC Report — Probate Source File Adapter + Operator Health

## Scope

Third no-send execution slice for the Harris + Montgomery probate autopilot PRD.

This slice adds a safe source-adapter bridge for local county export files and improves the operator-facing morning brief with anomaly/SLA signals.

## Implemented

- Added `app/services/probate_source_file_service.py`:
  - Reads local `.csv`, `.json`, and `.jsonl` probate source exports.
  - Groups rows into Harris/Montgomery source-row payloads.
  - Emits a `NightlySourcePullRequest`-compatible payload with `live_source_calls: false`, `no_send: true`, and provider sends disabled.
  - Distinguishes `county_scope` (counties present in the file) from `expected_counties` (default Harris + Montgomery autopilot expectation).
  - Rejects malformed JSON rows and unsupported/missing county rows instead of silently hiding bad source files.
- Added `scripts/probate_source_file_payload.py`:
  - CLI for converting a local source export into a no-send nightly-source-pull payload.
  - Supports stdout or output-file mode.
  - Works from outside the repo cwd via explicit repo-root path setup.
  - Restricts `--run-kind` to supported source-run kinds.
- Extended the morning brief with operator-helpful sections:
  - `sla_health`
  - `source_anomalies`
  - existing `source_quality`, `enrichment_backlog`, and `operator_next_actions` now have stronger tests.
- Added SLA/anomaly coverage for:
  - missing expected county lane;
  - source-count mismatches;
  - high invalid-row rate;
  - failed source lanes;
  - zero parse yield.

## Safety posture

No live county scraping was added.

No provider side effects were added:

- no HubSpot writes;
- no Instantly enrollment/activation/send;
- no SMS/Vapi/direct mail;
- no paid skiptrace;
- no hidden provider action behind the CLI or schedule.

The CLI only builds a local JSON payload. It does not post to Ares or call external providers.

## Verification

Captured in `test-output.txt`:

- `python -m pytest tests/services/test_nightly_lead_machine_service.py tests/services/test_probate_source_file_service.py tests/scripts/test_probate_source_file_payload.py tests/api/test_nightly_lead_machine.py tests/api/test_trigger_contract_files.py tests/api/test_runtime_config_contract.py tests/services/test_harris_probate_intake_service.py tests/services/test_probate_write_path_service.py tests/services/test_tax_overlay_service.py -q`
  - Result: `61 passed`
- `npm --prefix trigger run typecheck`
  - Result: pass
- `git diff --check`
  - Result: clean

## Review follow-ups handled

A delegated review flagged the main risk: a Harris-only file adapter payload initially did not prove missing Montgomery through the adapter path. Fixed by emitting explicit `expected_counties` and adding adapter-path SLA tests.

Additional hardening from review:

- JSON arrays now reject non-object rows with row context.
- Source files now reject missing/unsupported county rows instead of silently dropping them.
- CLI `--run-kind` now has explicit choices.
- CLI tests now cover stdout mode and execution from outside repo cwd.

## Remaining gates

- Real Harris browser/source adapter still needs implementation behind the no-send source-provider gate.
- Montgomery source discovery/browser adapter still needs implementation.
- The new file adapter is the safe bridge for exported county rows until live source adapters exist.
- CAD/property matching, tax overlay, land records, HubSpot mirror, and all outbound remain separate approval gates.
