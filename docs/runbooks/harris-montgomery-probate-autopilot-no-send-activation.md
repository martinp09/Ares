# Harris + Montgomery Probate Autopilot — No-Send Activation Runbook

- Status: draft / engineering handoff
- Updated UTC: 2026-05-15T21:36:35Z
- Scope: scheduled source acquisition, enrichment, scoring, briefing, and qualified-review preparation only
- Hard stop: no Instantly enrollment, no email/SMS/Vapi sends, no paid skiptrace, no HubSpot writes without separate approval gate

## Operating model

Ares remains the source of truth for source-run lifecycle, dedupe, enrichment state, scoring state, approval/suppression, and mirror eligibility. Trigger.dev only schedules the no-send runs. Mission Control remains the operator surface for aggregate health and next actions.

## Default-safe environment

Keep these defaults until an operator explicitly approves the next level:

```bash
LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=false
LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=false
LEAD_MACHINE_SOURCE_ADAPTER_PREVIEW_ENABLED=false
LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED=false
LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED=false
LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED=false
PROVIDER_LIVE_SENDS_ENABLED=false
INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=false
HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false
```

Durable state/artifact controls:

```bash
LEAD_MACHINE_SOURCE_RUNS_STATE_PATH=/path/to/durable/source-runs.json
LEAD_MACHINE_ARTIFACT_ROOT=/path/to/durable/artifacts
LEAD_MACHINE_BUSINESS_ID=<business-id>
LEAD_MACHINE_ENVIRONMENT=<environment>
```

## Schedule controls

Trigger schedules are registered at:

- `harris-montgomery-probate-0710-ct`: `10 7 * * *` America/Chicago
- `harris-montgomery-probate-1240-ct`: `40 12 * * *` America/Chicago
- `harris-montgomery-probate-1740-ct`: `40 17 * * *` America/Chicago
- `harris-montgomery-probate-0220-ct`: `20 2 * * *` America/Chicago
- `harris-montgomery-probate-weekly-sunday-0315-ct`: `15 3 * * 0` America/Chicago

With `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=false`, schedules create no-send placeholder/source-run control-plane records unless source rows are supplied through the file/export bridge. When source rows are present, the nightly source pull now runs the property/CAD, tax-overlay, and land-record/title-friction enrichment pass inside the same no-send runtime call, then emits aggregate morning-brief enrichment status plus internal stage artifacts.

With `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=true` and backend `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true`, the schedule payload requests:

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
    }
  }
}
```

Backend gate still rejects if approval, env gates, or no-send controls are missing.

## Live source adapter behavior

Implemented no-send source adapters:

- Harris County Clerk WebSearch probate date-window adapter
- Montgomery Odyssey Public Access civil/probate date-window adapter

Controls:

- `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true` required
- `source_provider_bridge.mode=live_source_adapters` required
- `source_provider_approval.approved=true` required
- `source_provider_approval.no_send=true` required
- `source_provider_approval.provider_sends_enabled=false` required
- No raw HTML is persisted; only row-level public case fields flow into source-row artifacts
- Browser automation is not used by the adapter; `browser_calls_attempted=false`

## Enrichment controls

The nightly source-pull path now invokes the property/tax/title enrichment service automatically for normalized `keep_now` probate rows when source rows are present. Local artifact enrichment remains the default input mode:

- `property_tax_title_enrichment.hcad_candidates_by_case`
- `property_tax_title_enrichment.tax_overlays_by_case`
- `property_tax_title_enrichment.tax_overlays_by_account`
- `property_tax_title_enrichment.land_record_rows_by_case`

The same pass writes internal zero-count source-run stage artifacts for:

- Harris: `harris_hcad_property_match`, `harris_hctax_overlay`, `harris_land_records`
- Montgomery: `montgomery_cad_property_match`, `montgomery_act_tax_overlay`, `montgomery_land_records`

Those enrichment stage runs do not inflate `new_record_count`; the morning brief reports completion/pending counts under `enrichment_backlog`. Live enrichment clients are still injectable and separately gated:

- `LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED=true` for CAD/property candidates
- `LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED=true` for public tax overlays
- `LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED=true` for land/title rows
- `enrichment_approval.approved=true` required
- `enrichment_approval.no_send=true` required
- `enrichment_approval.provider_sends_enabled=false` required
- Registered public clients are required for each requested live lane

The enrichment response always preserves:

- `no_send=true`
- `provider_sends_enabled=false`
- `outbound_allowed=false`
- `hubspot_mirror_blocked_until_approval_count`
- `outbound_blocked_until_explicit_approval_count`

## No-send smoke commands

Source-provider unit/contracts:

```bash
uv run pytest \
  tests/services/test_probate_source_provider_service.py \
  tests/services/test_probate_live_source_adapter_service.py \
  tests/services/test_nightly_lead_machine_service.py \
  tests/api/test_nightly_lead_machine.py -q
```

Enrichment unit/contracts:

```bash
uv run pytest tests/services/test_probate_property_tax_title_enrichment_service.py -q
```

Combined slice smoke:

```bash
uv run pytest \
  tests/services/test_probate_property_tax_title_enrichment_service.py \
  tests/services/test_probate_source_provider_service.py \
  tests/services/test_probate_live_source_adapter_service.py \
  tests/services/test_nightly_lead_machine_service.py \
  tests/api/test_nightly_lead_machine.py -q
```

Trigger typecheck:

```bash
npm --prefix trigger run typecheck
```

## Operator next actions

1. Keep scheduled live source calls disabled until durable state/artifact paths are configured.
2. Run file/export bridge first if live source adapters do not need to be activated yet.
3. When activating live source adapters, enable both schedule and backend source gates, then run one manual no-send source pull before enabling schedules.
4. Review source-run counts, county coverage, duplicate-case anomalies, and parser warnings in the morning brief / Mission Control health panel.
5. Only after source/enrichment quality is stable, design a separate qualified-only HubSpot mirror approval path.
6. Do not add Instantly/SMS send controls to this workflow.

## Failure modes

- Missing source approval: backend rejects before network calls.
- Missing live env gate: backend rejects before network calls.
- Montgomery Odyssey shape/session drift: source adapter raises parser/source error instead of silently publishing zero-row success.
- Parser count mismatch: source run records warnings and surfaces aggregate mismatch counts.
- Enrichment live flag without registered client: enrichment rejects before work.
- Any outbound/provider-send approval missing: outbound remains blocked.
