# Diff Summary — Harris Daily Lead Machine Foundation

## Scope
Backend + Trigger contract foundation for a Harris daily probate + HCAD `Estate Of` import path. No Slack posting, provider sends, Vercel deployment, or live hosted smoke were attempted.

## Changed files

- `app/services/harris_daily_lead_machine_service.py`
  - New deterministic daily import service for Harris probate records and HCAD `Estate Of` records.
  - Supports dry-run previews and repository-backed import when `dry_run=false`.
  - Produces QC warnings for duplicate Estate Of payloads, false-positive owner names, ambiguous tax overlay, multiple HCAD matches, and contact caps.
  - Keeps `provider_send_count=0` and reports Slack readiness/skip status only.

- `app/api/lead_machine.py`
  - Added `POST /lead-machine/harris/daily-import`.
  - Added request validation requiring at least one source payload.
  - Enhanced existing probate intake to forward per-record `hcad_candidates` into the write path.

- `app/core/config.py`
  - Added Slack readiness config fields: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_LEADS`, `SLACK_CHANNEL_HOT_LEADS`, `SLACK_CHANNEL_ERRORS`, `SLACK_CHANNEL_QC`.

- `trigger/src/lead-machine/runtime.ts`
  - Added `harrisDailyImport` endpoint key for `/lead-machine/harris/daily-import`.
  - Added TypeScript payload/response types for daily import runs.

- `trigger/src/lead-machine/harrisDailyImport.ts`
  - Added Trigger task wrapper `harris-daily-import` with lifecycle artifact type `lead_machine_harris_daily_import`.

- `tests/services/test_harris_daily_lead_machine_service.py`
  - Added service coverage for dry-run and non-dry-run paths, probate scoring, Estate Of CRM persistence, QC warnings, malformed source values, Slack-configured ready-not-sent status, and no provider sends.

- `tests/api/test_lead_machine.py`
  - Added route coverage for daily import success and missing-payload validation.
  - Updated probate intake stub expectations for HCAD candidate forwarding.

- `tests/api/test_trigger_contract_files.py`
  - Added static contract coverage for the Trigger daily import endpoint, task ID, and artifact key.

## Verification artifacts
- `test-output.txt` — focused service/API/Trigger contract tests.
- `full-pytest-output.txt` — full backend pytest run.
- `trigger-typecheck-output.txt` — Trigger TypeScript check.
- `diff-check-output.txt` — whitespace/diff check.
