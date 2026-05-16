# Harris + Montgomery Probate Autopilot — Live No-Send Activation Runbook

- Status: current / operational no-send / VPS env preflight healthy
- Updated UTC: 2026-05-16T15:59:30Z
- Scope: scheduled public source acquisition, public case-detail party/event/document/contact-candidate enrichment, public CAD/tax/land-record enrichment, scoring inputs, briefing, and qualified-review preparation
- Hard stop: no Instantly enrollment, no email/SMS/Vapi sends, no paid skiptrace, no HubSpot writes without separate approval gate

## Operating model

Ares remains the source of truth for source-run lifecycle, dedupe, enrichment state, scoring state, approval/suppression, and mirror/send eligibility. Trigger.dev is the intended long-term production scheduler, but Trigger cloud deploy is currently blocked by CLI login/auth in this environment. Until Trigger auth is recovered, Hermes no-agent cron job `815e1261ab2e` is the active no-send CT scheduler/watchdog; it reads `/opt/ares/Ares/.env`, runs from `/opt/ares/Ares`, writes durable state/artifacts under `/var/lib/ares/lead-machine`, and keeps all provider/outbound gates false. Mission Control is the aggregate operator surface. HubSpot is a mirror/operator view only after separate approval. Instantly is delivery only after future explicit campaign approval.

Manual experiments and operator-triggered replays must use `source_run_scope=manual`; scheduled Trigger.dev/background runs must use `source_run_scope=autonomous`. Dedupe comparisons are scoped by this field so a manual scrape cannot poison, replay, or suppress the autonomous background queue.

## Operational environment defaults

The PRD execution default is operational, not scaffold-only. These live intelligence lanes default on in code and in the Trigger schedule payload builder:

```bash
LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true
LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_CASE_DETAIL_CALLS_ENABLED=true
LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED=true
LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED=true
```

Outbound/provider mutation gates remain off until Martin approves exact recipients/campaigns:

```bash
PROVIDER_LIVE_SENDS_ENABLED=false
INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=false
HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false
VAPI_PROVIDER_LIVE_SENDS_ENABLED=false
```

Durable state/artifact controls for production deployment:

```bash
# Supabase is required for the durable production identity ledger; memory is local-only.
LEAD_MACHINE_BACKEND=supabase

# The state file parent and artifact root must already exist and be writable by the runtime user.
LEAD_MACHINE_SOURCE_RUNS_STATE_PATH=/var/lib/ares/lead-machine/source-runs.json
LEAD_MACHINE_ARTIFACT_ROOT=/var/lib/ares/lead-machine/artifacts

# Use the production business slug or numeric business_id that resolves in public.businesses.
LEAD_MACHINE_BUSINESS_ID=<business-slug-or-id>
LEAD_MACHINE_ENVIRONMENT=prod
```

Run the read-only environment preflight before deployment or schedule activation. It does not create files/directories, call county sources, or mutate providers:

```bash
uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live
```

Preflight must report `status=healthy`, `no_send_ok=true`, `live_intelligence_ready=true`, and no blockers before a production no-send rollout.

If the preflight is blocked by missing durable env, make only operator-side config changes; do not commit secrets to the repo:

```bash
sudo install -d -m 0750 -o <runtime-user> -g <runtime-group> /var/lib/ares/lead-machine
sudo install -d -m 0750 -o <runtime-user> -g <runtime-group> /var/lib/ares/lead-machine/artifacts
# Then set the non-secret controls above plus existing Supabase service credentials in the runtime env manager.
```

Production VPS deployment note: `/opt/ares/Ares/.env` now uses `LEAD_MACHINE_BUSINESS_ID=limitless` and `LEAD_MACHINE_ENVIRONMENT=prod`; read-only tenant resolution verified that `limitless/prod` resolves to business PK `1`.

Future deployment/schedule changes remain blocked until the same deployed runtime environment that Trigger/API will use passes the preflight with `--require-scheduled-live`. Current VPS status: **preflight healthy** as of QC `docs/qc/2026-05-16/probate-production-readiness-wrap/`.

## Schedule controls

Trigger schedule definitions are in code at:

- `harris-montgomery-probate-0710-ct`: `10 7 * * *` America/Chicago
- `harris-montgomery-probate-1240-ct`: `40 12 * * *` America/Chicago
- `harris-montgomery-probate-1740-ct`: `40 17 * * *` America/Chicago
- `harris-montgomery-probate-0220-ct`: `20 2 * * *` America/Chicago
- `harris-montgomery-probate-weekly-sunday-0315-ct`: `15 3 * * 0` America/Chicago

The schedule payload now emits source, case-detail, and property/tax/title enrichment no-send approval metadata by default:

```json
{
  "live_source_calls": true,
  "metadata": {
    "source_provider_bridge": {
      "mode": "live_source_adapters",
      "expected_counties": ["harris", "montgomery"]
    },
    "source_run_scope": "autonomous",
    "source_provider_approval": {
      "approved": true,
      "approved_by": "trigger-schedule-env-gate",
      "scope": "harris_montgomery_probate_public_sources",
      "no_send": true,
      "provider_sends_enabled": false
    },
    "case_detail_enrichment": {
      "live_case_detail_calls": true,
      "case_detail_approval": {
        "approved": true,
        "approved_by": "trigger-schedule-env-gate",
        "scope": "harris_montgomery_probate_public_case_detail_pages",
        "no_send": true,
        "provider_sends_enabled": false
      }
    },
    "property_tax_title_enrichment": {
      "live_cad_calls": true,
      "live_tax_calls": true,
      "live_land_record_calls": true,
      "enrichment_approval": {
        "approved": true,
        "approved_by": "trigger-schedule-env-gate",
        "scope": "harris_montgomery_probate_public_cad_tax_land_records",
        "no_send": true,
        "provider_sends_enabled": false
      }
    }
  }
}
```

Backend runtime calls still reject before live work if approval metadata is missing, if no-send constraints are false, if public case-detail URLs are outside the approved county allowlist, or if outbound provider-send flags are true.

## Dedupe and manual/autonomous isolation

Current runtime guardrails:

- Source identity is `probate_case_sha256:{sha256("probate_case:{county}:{normalized_case_number}")}` using version `county_case_sha256_v1`; raw case numbers stay in internal source artifacts, while dedupe summaries can use aggregate counts.
- Before building source-run manifests, the nightly service loads prior completed probate source runs for the same `business_id`, `environment`, and `source_run_scope`. With `LEAD_MACHINE_BACKEND=supabase`, it first reads durable same-scope keys from `public.probate_source_identities`, then overlays any file-backed completed runs still present in the local runtime ledger.
- After a Harris/Montgomery probate source run completes, the nightly service records normalized source identities back to `public.probate_source_identities` when the lead-machine backend is Supabase. Hashed `source_identity_records` in run metadata provide a non-PII fallback when artifact paths are logical/non-local. Manual isolated environments such as `<environment>-manual` skip remote identity reads/writes.
- Remote identity ledger read/write failures are downgraded to sanitized warnings; the nightly path continues with file-backed dedupe and still saves the morning brief/idempotency response.
- `record_count` and `keep_now_count` for the run only include new unique rows. Rows seen in prior same-scope source runs are written to `duplicate_prior_run_rows` artifacts and counted in `source_quality.duplicate_prior_run_count` / `source_quality.deduped_existing_record_count`.
- Duplicate rows inside the same source packet are written to `duplicate_current_run_rows` and counted in `source_quality.duplicate_current_run_count`.
- Trigger.dev schedule payloads set `source_run_scope=autonomous`.
- Forced/manual Hermes runner executions use a separate manual ledger path and `LEAD_MACHINE_ENVIRONMENT=<environment>-manual`, plus `source_run_scope=manual`, so manual experiments cannot mutate autonomous source-run state or suppress autonomous records.
- Supabase migration `20260516131500_probate_source_identity_dedupe.sql` defines `public.probate_source_identities` with unique `(business_id, environment, source_run_scope, county, source_identity_key)` for the durable control-plane version of the same boundary; adapter QC is `docs/qc/2026-05-16/probate-source-identity-supabase-adapter/`.

## Live source adapter behavior

Implemented no-send source adapters:

- Harris County Clerk WebSearch probate date-window adapter
- Montgomery Odyssey Public Access civil/probate date-window adapter

Controls:

- `live_source_calls=true` required on the runtime request
- `source_provider_bridge.mode=live_source_adapters` required
- `source_provider_approval.approved=true` required
- `source_provider_approval.no_send=true` required
- `source_provider_approval.provider_sends_enabled=false` required
- No raw HTML is persisted; only public row-level case fields flow into internal source-row artifacts
- Browser automation is not used by the adapter; `browser_calls_attempted=false`

## Enrichment behavior

The nightly source-pull path invokes case-detail enrichment first, then property/tax/title enrichment, for normalized `keep_now` probate rows when source rows are present.

Case-detail enrichment extracts aggregate-safe evidence from public county case-detail pages or approved fixture payloads:

- parties and normalized roles
- hearing/event clues
- document references
- attorney/professional-contact clues
- capped contact-candidate packets with `is_confirmed_seller=false`, `seller_authority_verified=false`, `skiptrace_status=not_requested`, and `outbound_allowed=false`

Live case-detail fetches require `case_detail_approval.approved=true`, `case_detail_approval.no_send=true`, `case_detail_approval.provider_sends_enabled=false`, and an HTTPS county-detail URL on the allowlist:

- `www.cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx`
- `cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx`
- `odyssey.mctx.org/County/CaseDetail.aspx`

Registered public clients:

- Harris property/tax candidate lookup through public HCTax delinquent search + statement flow
- Harris land-record metadata through public County Clerk real-property search
- Montgomery CAD/property lookup through public MCAD ArcGIS parcel layer
- Montgomery tax overlay through public ACT Web tax detail flow
- Montgomery land-record metadata through public PublicSearch shell / review-needed fallback

The pass writes internal stage lanes for:

- Harris: `harris_probate_case_detail`, `harris_hcad_property_match`, `harris_hctax_overlay`, `harris_land_records`
- Montgomery: `montgomery_probate_case_detail`, `montgomery_cad_property_match`, `montgomery_act_tax_overlay`, `montgomery_land_records`

Those enrichment stage runs do not inflate `new_record_count`; the morning brief reports completion/pending/review counts under `enrichment_backlog`.

The enrichment response always preserves:

- `no_send=true`
- `provider_sends_enabled=false`
- `outbound_allowed=false`
- case-detail aggregate counts only: `detail_completed_count`, `detail_incomplete_count`, `detail_blocked_count`, `party_count`, `event_count`, `document_reference_count`, `contact_candidate_count`, `primary_contact_candidate_count`
- no seller-authority assertion from probate parties alone
- `hubspot_mirror_blocked_until_approval_count`
- `outbound_blocked_until_explicit_approval_count`

## No-send smoke commands

Live operational smoke against public sources/CAD/tax/land clients:

```bash
uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD
```

Combined focused contracts:

```bash
uv run pytest \
  tests/services/test_probate_live_source_adapter_service.py \
  tests/services/test_probate_case_detail_enrichment_service.py \
  tests/services/test_probate_property_tax_title_enrichment_service.py \
  tests/services/test_probate_source_provider_service.py \
  tests/services/test_nightly_lead_machine_service.py \
  tests/api/test_nightly_lead_machine.py \
  tests/api/test_lead_machine_trigger_contract.py \
  tests/api/test_trigger_contract_files.py -q
```

Full backend and Trigger verification:

```bash
uv run pytest -q
npm --prefix trigger run typecheck
```

Latest evidence:

- Production readiness wrap QC folder: `docs/qc/2026-05-16/probate-production-readiness-wrap/`
- Code commit deployed to VPS Docker: `fc99b75 Harden probate production readiness`
- VPS production env preflight after config: `status=healthy`, `no_send_ok=true`, `live_intelligence_ready=true`, `blockers=[]`; artifact `env-preflight-after-config.json`.
- `/opt/ares/Ares` is detached at `fc99b75`; `ares-api` and `ares-ui` Docker image labels are `fc99b75`; `ares-api` has `/var/lib/ares/lead-machine` mounted read-write.
- Production tenant resolution: `limitless/prod` resolves to business PK `1`; artifact `tenant-resolution-output.txt`.
- Production health smoke: `/health` 200 and UI 200; Mission Control probate health for `limitless/prod` returns `status=no_data` until the first post-deploy autonomous prod brief is created.
- Trigger cloud deploy status: blocked by Trigger CLI login/auth; artifact `trigger-deploy-output-sanitized.txt`. Trigger remains the intended long-term scheduler after auth recovery.
- Hermes no-agent cron job `815e1261ab2e` is the active no-send CT scheduler/watchdog until Trigger auth is fixed; the script now reads `/opt/ares/Ares/.env`, runs from `/opt/ares/Ares`, writes durable state/artifacts under `/var/lib/ares/lead-machine`, and keeps outbound/provider gates false.
- Manual forced Hermes smoke: completed under isolated `prod-manual` with zero current-day rows, `sla_status=healthy`, `no_send_ok=true`, `outbound_allowed=false`, provider side effects all false, and live CAD/tax/land attempted true.
- Post-adapter live no-send monitor QC folder: `docs/qc/2026-05-16/probate-post-adapter-live-no-send-monitor/`
- Same-day 2026-05-16 strict smoke: failed/inconclusive because the valid zero-row day produced no passing summary JSON; treat zero-row source windows as non-errors in runtime but do not count that artifact as a green smoke.
- Two-day 2026-05-15→2026-05-16 live no-send monitor: `48` source records, `8` keep-now rows, `8` enriched rows, `source_health_failed_runs=0`, `warnings_count=0`, `sla_status=healthy`, `no_send=true`, and `provider_sends_enabled=false`.
- Harris case-detail monitor correction: live Harris rows currently expose postback-only detail targets, now classified as `case_detail_incomplete_count=8` / `case_detail_blocked_count=0` instead of unsafe blocked URLs. A full postback detail client remains a follow-up if case-detail completion is required from live Harris rows.
- Focused production-readiness contracts: `52 passed`
- Full backend: `966 passed`
- Trigger typecheck: passed
- Supabase source identity adapter QC folder: `docs/qc/2026-05-16/probate-source-identity-supabase-adapter/`
- Focused identity/nightly/source-file contracts: `43 passed`
- Full backend: `961 passed`
- Trigger typecheck: passed
- Dedupe/manual-isolation hardening QC folder: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`
- Local autonomous ledger comparison, latest two dates: 2026-05-15 had 39 Harris / 8 Montgomery source identities; 2026-05-16 had 0 Harris / 0 Montgomery source identities; overlap count was 0 for both counties, with no raw PII printed.
- Dedupe/runtime/schema focused contracts: `36 passed`
- Backend db+services suite: `466 passed`
- Trigger typecheck: passed
- Case-detail QC folder: `docs/qc/2026-05-15/probate-case-detail-enrichment/`
- Focused case-detail/source/nightly/env/Trigger contracts: `47 passed`
- Full backend: `916 passed`
- Trigger typecheck: passed
- Historical live smoke: `47` source records, `8` keep-now enriched, `sla_status=healthy`, `source_health_failed_runs=0`, no sends; QC folder `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`

## Operator next actions

1. Watch the next Hermes no-agent CT window (or Trigger once auth is recovered) for the first post-deploy `limitless/prod` autonomous morning brief; Mission Control currently reports `status=no_data` for prod until that run exists.
2. Recover Trigger.dev CLI auth and deploy `trigger/` from `fc99b75` or newer; when Trigger is authoritative, pause/retire the Hermes autonomous schedule to avoid duplicate source runs.
3. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required; current postback-only rows are safely incomplete, not blocked.
4. Continue monitoring source-run counts, county coverage, parser warnings, duplicate-prior-run counts, enrichment backlog, and no-send confirmation in the morning brief / Mission Control health panel.
5. Only after source/enrichment quality is stable, design a separate qualified-only HubSpot mirror approval path.
6. Do not add Instantly/SMS send controls to this workflow without exact campaign/recipient approval.

## Failure modes

- Missing source approval: backend rejects before network calls.
- Missing case-detail approval: case-detail enrichment records blocked/incomplete rows before live detail-page calls.
- Missing enrichment approval: enrichment rejects before live CAD/tax/land work.
- Disallowed case-detail URL: live case-detail fetch is blocked unless the HTTPS URL matches the approved Harris/Montgomery public case-detail allowlist.
- Harris postback-only case-detail link: live source rows preserve the postback target and case-detail enrichment marks the row incomplete with `case_detail_postback_only`; a dedicated postback client is required before those rows can complete party/event/document extraction.
- Montgomery Odyssey shape/session drift: source adapter retries bounded sessions, then raises parser/source error instead of silently publishing zero-row success.
- Parser count mismatch: source run records warnings and surfaces aggregate mismatch counts.
- Property identifiers missing from probate rows: case-detail-derived parties/addresses/context are available for downstream matching, but property match remains pending/unmatched until deterministic CAD confidence clears.
- Any outbound/provider-send approval missing: outbound remains blocked.
