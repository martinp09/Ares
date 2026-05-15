# QC Report — Probate Autopilot Durable Source Rows

## Scope

Second no-send execution slice for the Harris + Montgomery probate autopilot PRD.

This slice turns the Phase 1 schedule/source-run shell into a more durable ingestion foundation:

- Adds optional file-backed source-run repository state via `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`.
- Persists source runs, morning briefs, nightly idempotency responses, and morning-brief idempotency responses across process restarts when the state path is configured.
- Uses file locking, reload-before-save, and atomic replace writes for JSON state.
- Adds predictable `SourceRunsPersistenceError` for corrupt source-run state files.
- Adds optional raw artifact writing via `LEAD_MACHINE_ARTIFACT_ROOT`.
- Adds Harris/Montgomery source-row ingestion from request metadata (`source_rows`) without live scraping.
- Writes raw, normalized, keep-now, and invalid-row JSONL artifacts when an artifact root is configured.
- Adds source-row normalization/keep-now classification for both Harris and Montgomery lanes using the existing keep-now rules.
- Expands the morning brief with invented operator-helpful sections:
  - `source_quality`
  - `enrichment_backlog`
  - `operator_next_actions`

## Safety posture

No live county scraping was added.

No provider side effects were added:

- no HubSpot writes;
- no Instantly enrollment/activation/send;
- no SMS/Vapi/direct mail;
- no paid skiptrace;
- no provider action hidden behind the schedule.

The new source-row ingestion path consumes rows already supplied to Ares. It does not fetch remote county pages by itself.

## Verification

Captured in `test-output.txt`:

- `python -m pytest tests/services/test_nightly_lead_machine_service.py tests/api/test_nightly_lead_machine.py tests/api/test_trigger_contract_files.py tests/api/test_runtime_config_contract.py tests/services/test_harris_probate_intake_service.py tests/services/test_probate_write_path_service.py tests/services/test_tax_overlay_service.py -q`
  - Result: `49 passed`
- `npm --prefix trigger run typecheck`
  - Result: pass
- `git diff --check`
  - Result: clean

## Remaining gates

- Real Harris County Clerk source adapter/browser bridge still needs implementation.
- Montgomery probate source discovery/adapter still needs implementation.
- File-backed source-run state is a safe durable local foundation; Supabase-backed source-run persistence is still a later production-hardening option if multi-instance runtime needs it.
- CAD/property matching, tax overlays, land-record pass, HubSpot mirror, and copy generation remain separate phases/gates.
- All outbound/provider actions remain blocked until explicit operator approval.
