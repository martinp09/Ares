# Harris + Montgomery Probate Autopilot — Live No-Send Activation Runbook

- Status: current / operational no-send
- Updated UTC: 2026-05-15T22:59:40Z
- Scope: scheduled public source acquisition, public CAD/tax/land-record enrichment, scoring inputs, briefing, and qualified-review preparation
- Hard stop: no Instantly enrollment, no email/SMS/Vapi sends, no paid skiptrace, no HubSpot writes without separate approval gate

## Operating model

Ares remains the source of truth for source-run lifecycle, dedupe, enrichment state, scoring state, approval/suppression, and mirror/send eligibility. Trigger.dev schedules the no-send runs. Mission Control is the aggregate operator surface. HubSpot is a mirror/operator view only after separate approval. Instantly is delivery only after future explicit campaign approval.

## Operational environment defaults

The PRD execution default is operational, not scaffold-only. These live intelligence lanes default on in code and in the Trigger schedule payload builder:

```bash
LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true
LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED=true
LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED=true
LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED=true
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

The schedule payload now emits both source and enrichment no-send approval metadata by default:

```json
{
  "live_source_calls": true,
  "metadata": {
    "source_provider_bridge": {
      "mode": "live_source_adapters",
      "expected_counties": ["harris", "montgomery"]
    },
    "source_provider_approval": {
      "approved": true,
      "approved_by": "trigger-schedule-env-gate",
      "scope": "harris_montgomery_probate_public_sources",
      "no_send": true,
      "provider_sends_enabled": false
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

Backend runtime calls still reject before live work if approval metadata is missing, if no-send constraints are false, or if outbound provider-send flags are true.

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

The nightly source-pull path invokes property/tax/title enrichment automatically for normalized `keep_now` probate rows when source rows are present.

Registered public clients:

- Harris property/tax candidate lookup through public HCTax delinquent search + statement flow
- Harris land-record metadata through public County Clerk real-property search
- Montgomery CAD/property lookup through public MCAD ArcGIS parcel layer
- Montgomery tax overlay through public ACT Web tax detail flow
- Montgomery land-record metadata through public PublicSearch shell / review-needed fallback

The pass writes internal stage lanes for:

- Harris: `harris_hcad_property_match`, `harris_hctax_overlay`, `harris_land_records`
- Montgomery: `montgomery_cad_property_match`, `montgomery_act_tax_overlay`, `montgomery_land_records`

Those enrichment stage runs do not inflate `new_record_count`; the morning brief reports completion/pending/review counts under `enrichment_backlog`.

The enrichment response always preserves:

- `no_send=true`
- `provider_sends_enabled=false`
- `outbound_allowed=false`
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

- QC folder: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`
- Live smoke: `47` source records, `8` keep-now enriched, `sla_status=healthy`, `source_health_failed_runs=0`, no sends
- Focused tests: `75 passed`
- Full backend: `901 passed`
- Trigger typecheck: passed

## Operator next actions

1. Before deploying a build that includes this preflight, run the env preflight and configure durable state/artifact paths.
2. Monitor source-run counts, county coverage, parser warnings, enrichment backlog, and no-send confirmation in the morning brief / Mission Control health panel.
3. Only after source/enrichment quality is stable, design a separate qualified-only HubSpot mirror approval path.
4. Do not add Instantly/SMS send controls to this workflow without exact campaign/recipient approval.

## Failure modes

- Missing source approval: backend rejects before network calls.
- Missing enrichment approval: enrichment rejects before live CAD/tax/land work.
- Montgomery Odyssey shape/session drift: source adapter retries bounded sessions, then raises parser/source error instead of silently publishing zero-row success.
- Parser count mismatch: source run records warnings and surfaces aggregate mismatch counts.
- Property identifiers missing from probate rows: property match remains pending/unmatched while tax/title review can still record attempted live evidence.
- Any outbound/provider-send approval missing: outbound remains blocked.
