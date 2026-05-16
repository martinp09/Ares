# Probate autopilot dedupe + runtime isolation QC

- Date: 2026-05-16
- Scope: Harris + Montgomery probate no-send source-run dedupe, Trigger.dev scheduled scope, Supabase durable identity contract, and Hermes manual-run isolation.
- Hard boundary: no Instantly enrollment, no sends, no SMS/Vapi, no paid skiptrace, no HubSpot writes.

## What changed

- Added stable source identity generation for probate source rows:
  - format: `probate_case_sha256:{sha256("probate_case:{county}:{normalized_case_number}")}`
  - version: `county_case_sha256_v1`
- Nightly source-pull now loads prior completed probate source runs for the same `business_id`, `environment`, and `source_run_scope` before building manifests.
- Prior same-scope duplicates are excluded from `record_count`, `keep_now_count`, and in-run enrichment; they are preserved in `duplicate_prior_run_rows` artifacts.
- Same-packet duplicates after the first occurrence are excluded and preserved in `duplicate_current_run_rows` artifacts.
- Morning brief `source_quality` now reports:
  - `duplicate_prior_run_count`
  - `duplicate_current_run_count`
  - `deduped_existing_record_count`
- Trigger.dev schedule payloads now emit `source_run_scope=autonomous`.
- Hermes forced/manual script path is isolated from the autonomous runner:
  - manual state: `/opt/ares/lead-data/probate_autopilot/manual_runs/state/source-runs.json`
  - manual artifacts: `/opt/ares/lead-data/probate_autopilot/manual_runs/artifacts`
  - manual lock: `/opt/ares/lead-data/probate_autopilot/manual_runs/locks/runner.lock`
  - manual environment: `<LEAD_MACHINE_ENVIRONMENT>-manual`
- Supabase migration added: `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql`
  - table: `public.probate_source_identities`
  - unique key: `(business_id, environment, source_run_scope, county, source_identity_key)`

## Current autonomous ledger comparison

Command used only aggregate counts and hashed/generated identities; raw case numbers or party names were not printed.

- Ledger: `/opt/ares/lead-data/probate_autopilot/state/source-runs.json`
- Total source-run records in local ledger: 14
- Scope counts: manual 10, autonomous 4
- Autonomous dates present: `2026-05-15`, `2026-05-16`

Latest-date comparison:

- 2026-05-15 Harris:
  - runs: 1
  - parsed: 39
  - record_count: 39
  - identity_count: 39
  - duplicate_prior_run_count: 0
  - duplicate_current_run_count: 0
- 2026-05-15 Montgomery:
  - runs: 1
  - parsed: 8
  - record_count: 8
  - identity_count: 8
  - duplicate_prior_run_count: 0
  - duplicate_current_run_count: 0
- 2026-05-16 Harris:
  - runs: 1
  - parsed: 0
  - record_count: 0
  - identity_count: 0
  - duplicate_prior_run_count: 0
  - duplicate_current_run_count: 0
- 2026-05-16 Montgomery:
  - runs: 1
  - parsed: 0
  - record_count: 0
  - identity_count: 0
  - duplicate_prior_run_count: 0
  - duplicate_current_run_count: 0

Overlap check:

- Harris `2026-05-15 -> 2026-05-16`: yesterday_ids 39, today_ids 0, overlap_count 0, today_new_vs_yesterday 0
- Montgomery `2026-05-15 -> 2026-05-16`: yesterday_ids 8, today_ids 0, overlap_count 0, today_new_vs_yesterday 0

Interpretation: today's autonomous background ledger currently has zero parsed source identities, so there are no duplicate today-vs-yesterday scraped leads in the local autonomous ledger. Future non-empty runs will be compared against prior same-scope completed source identities before `record_count`, `keep_now_count`, and enrichment are computed.

## Verification commands

```bash
git diff --check
uv run pytest tests/services/test_nightly_lead_machine_service.py tests/services/test_probate_source_file_service.py tests/db/test_probate_source_identity_schema.py -q
python3 -m py_compile /root/.hermes/scripts/ares_probate_autopilot_no_send.py
uv run pytest tests/db tests/services -q
npm run typecheck  # from trigger/
```

## Verification results

- Focused nightly/source-file/dedupe/Supabase schema tests: `36 passed in 0.48s`
- Backend DB + services suite: `466 passed in 2.57s`
- Trigger.dev worker typecheck: passed
- Python compile for `/root/.hermes/scripts/ares_probate_autopilot_no_send.py`: passed
- `git diff --check`: passed

## Files changed

- `app/services/probate_autopilot_manifest_service.py`
- `app/services/nightly_lead_machine_service.py`
- `trigger/src/lead-machine/probateAutopilotSchedules.ts`
- `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql`
- `tests/services/test_probate_source_file_service.py`
- `tests/db/test_probate_source_identity_schema.py`
- `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- `/root/.hermes/scripts/ares_probate_autopilot_no_send.py` (runtime script used by Hermes cron job `815e1261ab2e`)

## Open follow-up

- Wire the Supabase `probate_source_identities` table into the production source-run persistence adapter when the lead-machine runtime moves from the current file-backed source-run repository into Supabase for this lane.
