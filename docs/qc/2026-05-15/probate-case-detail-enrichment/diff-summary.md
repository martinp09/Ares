# Diff Summary — Probate Case-Detail Enrichment

## Added

- `app/services/probate_case_detail_enrichment_service.py`
  - Deterministic no-send case-detail enrichment for keep-now probate rows.
  - Extracts parties/roles, event and hearing clues, document references, attorney/professional clues, and contact-candidate packets.
  - Caps primary contact candidates and keeps `is_confirmed_seller=false`, `seller_authority_verified=false`, `skiptrace_status=not_requested`, and `outbound_allowed=false`.
  - Blocks live fetches unless no-send approval metadata is present and the detail URL is on the approved public county allowlist.
- `tests/services/test_probate_case_detail_enrichment_service.py`
  - Covers fixture extraction, no-approval live blocking, URL allowlist blocking, and approved live-client execution.
- `docs/qc/2026-05-15/probate-case-detail-enrichment/`
  - Aggregate-only QC evidence for this slice.

## Updated runtime/backend

- `app/core/config.py`
  - Added `LEAD_MACHINE_LIVE_CASE_DETAIL_CALLS_ENABLED` defaulting on for operational no-send intelligence.
- `app/models/source_runs.py`
  - Added source-run lanes: `harris_probate_case_detail`, `montgomery_probate_case_detail`.
- `app/services/nightly_lead_machine_service.py`
  - Runs case-detail enrichment before property/tax/title enrichment for probate autopilot keep-now rows.
  - Writes aggregate case-detail artifacts and source-run manifests without inflating source `new_record_count`.
  - Adds case-detail summary/backlog/operator-action fields.
- `app/services/probate_live_source_adapter_service.py`
  - Preserves Harris/Montgomery public case-detail URLs from live source rows where available.
- `app/services/probate_source_adapter_service.py`
  - Normalizes `case_detail_url` / `detail_url` / `case_url` aliases from source rows.
- `scripts/probate_autopilot_env_contract.py`
  - Requires explicit live/scheduled case-detail env gates in no-send scheduled-live preflight.

## Updated Trigger contracts

- `trigger/src/lead-machine/probateAutopilotSchedules.ts`
  - Adds `LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED`.
  - Emits no-send case-detail approval metadata in scheduled probate payloads.
- `trigger/src/lead-machine/runtime.ts`
  - Adds case-detail source-run lanes to the TypeScript lane union.

## Updated tests

- `tests/services/test_nightly_lead_machine_service.py`
  - Verifies nightly source-pull runs case-detail before property/tax/title enrichment and reports aggregate backlog/contact-candidate counts.
- `tests/services/test_probate_live_source_adapter_service.py`
  - Verifies Harris/Montgomery live parsers preserve case-detail URLs without HTML artifacts.
- `tests/api/test_trigger_contract_files.py`
  - Verifies scheduled payloads include live case-detail env gate and no-send metadata.
- `tests/scripts/test_probate_autopilot_env_contract.py`
  - Verifies case-detail env gates are part of healthy no-send preflight.

## Updated docs

- `.env.example`
- `README.md`
- `CONTEXT.md`
- `TODO.md`
- `memory.md`
- `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- Historical QC reports now point to this superseding case-detail slice where relevant.
- Obsidian PRD: `/root/obsidian-vault/03-Experiments/Harris Montgomery Probate Autopilot PRD.md`

## Side-effect boundary

No production deploy, live provider send, Instantly enrollment, SMS/Vapi, paid skiptrace, HubSpot write, Slack/provider send, or live county smoke was executed in this slice.
