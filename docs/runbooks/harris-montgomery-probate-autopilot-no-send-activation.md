# Harris + Montgomery Probate Autopilot — Live No-Send Activation Runbook

- Status: current / operational no-send
- Updated UTC: 2026-05-16T13:10:45Z
- Scope: scheduled public source acquisition, public case-detail party/event/document/contact-candidate enrichment, public CAD/tax/land-record enrichment, scoring inputs, briefing, and qualified-review preparation
- Hard stop: no Instantly enrollment, no email/SMS/Vapi sends, no paid skiptrace, no HubSpot writes without separate approval gate

## Operating model

Ares remains the source of truth for source-run lifecycle, dedupe, enrichment state, scoring state, approval/suppression, and mirror/send eligibility. Trigger.dev schedules the no-send runs. Mission Control is the aggregate operator surface. HubSpot is a mirror/operator view only after separate approval. Instantly is delivery only after future explicit campaign approval.

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
```

Durable state/artifact controls for production deployment:

```bash
LEAD_MACHINE_SOURCE_RUNS_STATE_PATH=/path/to/durable/source-runs.json
LEAD_MACHINE_ARTIFACT_ROOT=/path/to/durable/artifacts
LEAD_MACHINE_BUSINESS_ID=<business-id>
LEAD_MACHINE_ENVIRONMENT=<environment>
```

Run the read-only environment preflight before deployment or schedule activation. It does not create files/directories, call county sources, or mutate providers:

```bash
uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live
```

Preflight must report `status=healthy`, `no_send_ok=true`, `live_intelligence_ready=true`, and no blockers before a production no-send rollout.

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
- Before building source-run manifests, the nightly service loads prior completed probate source runs for the same `business_id`, `environment`, and `source_run_scope`.
- `record_count` and `keep_now_count` for the run only include new unique rows. Rows seen in prior same-scope source runs are written to `duplicate_prior_run_rows` artifacts and counted in `source_quality.duplicate_prior_run_count` / `source_quality.deduped_existing_record_count`.
- Duplicate rows inside the same source packet are written to `duplicate_current_run_rows` and counted in `source_quality.duplicate_current_run_count`.
- Trigger.dev schedule payloads set `source_run_scope=autonomous`.
- Forced/manual Hermes runner executions use a separate manual ledger path and `LEAD_MACHINE_ENVIRONMENT=<environment>-manual`, plus `source_run_scope=manual`, so manual experiments cannot mutate autonomous source-run state or suppress autonomous records.
- Supabase migration `20260516131500_probate_source_identity_dedupe.sql` defines `public.probate_source_identities` with unique `(business_id, environment, source_run_scope, county, source_identity_key)` for the durable control-plane version of the same boundary.

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

1. Before deploying a build that includes this preflight, run the env preflight and configure durable state/artifact paths.
2. Monitor source-run counts, county coverage, parser warnings, enrichment backlog, and no-send confirmation in the morning brief / Mission Control health panel.
3. Only after source/enrichment quality is stable, design a separate qualified-only HubSpot mirror approval path.
4. Do not add Instantly/SMS send controls to this workflow without exact campaign/recipient approval.

## Failure modes

- Missing source approval: backend rejects before network calls.
- Missing case-detail approval: case-detail enrichment records blocked/incomplete rows before live detail-page calls.
- Missing enrichment approval: enrichment rejects before live CAD/tax/land work.
- Disallowed case-detail URL: live case-detail fetch is blocked unless the HTTPS URL matches the approved Harris/Montgomery public case-detail allowlist.
- Montgomery Odyssey shape/session drift: source adapter retries bounded sessions, then raises parser/source error instead of silently publishing zero-row success.
- Parser count mismatch: source run records warnings and surfaces aggregate mismatch counts.
- Property identifiers missing from probate rows: case-detail-derived parties/addresses/context are available for downstream matching, but property match remains pending/unmatched until deterministic CAD confidence clears.
- Any outbound/provider-send approval missing: outbound remains blocked.
