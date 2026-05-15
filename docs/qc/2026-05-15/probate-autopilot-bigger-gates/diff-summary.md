# Diff Summary — Probate Autopilot Bigger Gates

## Added

- `app/services/probate_property_tax_title_enrichment_service.py`
  - No-send enrichment service for supplied local property/CAD candidates, tax overlay snapshots, and land-record/title-friction rows.
- `tests/services/test_probate_property_tax_title_enrichment_service.py`
  - Covers local artifact enrichment, live-flag rejection, and approval-blocked downstream states.
- `trigger/src/lead-machine/probatePropertyTaxTitleEnrichment.ts`
  - Trigger wrapper for the enrichment endpoint without raw-response artifact publication.
- `docs/qc/2026-05-15/probate-autopilot-bigger-gates/`
  - QC report, diff summary, and verification output.

## Modified

- `.env.example`
  - Documents default-off source/live gates.
- `app/core/config.py`
  - Adds `lead_machine_source_adapter_preview_enabled` / `LEAD_MACHINE_SOURCE_ADAPTER_PREVIEW_ENABLED`.
- `app/services/probate_source_provider_service.py`
  - Adds `adapter_preview` dry-run bridge mode with explicit approval and no network/browser calls.
- `app/services/probate_autopilot_manifest_service.py`
  - Allows safe adapter-preview metadata into source-run manifest metadata.
- `app/api/lead_machine.py`
  - Adds internal property/tax/title enrichment endpoint and outbound `operator_approval` payload field.
- `trigger/src/lead-machine/runtime.ts`
  - Adds endpoint/types for enrichment and `operator_approval` in outbound enqueue payload.
- `app/services/lead_outbound_service.py`
  - Adds service-level outbound operator/global/provider gate before provider call or run writes.
- `app/services/probate_write_path_service.py`
  - Adds write-path outbound preflight before Instantly client construction and passes settings to outbound service.
- Tests under `tests/api/` and `tests/services/`
  - Cover adapter preview gates, no-send enrichment, Trigger contract, outbound approval/live gates, and write-path preflight.

## Intentional non-changes

- No real Harris/Montgomery network/browser adapter implementation.
- No provider mutation buttons in Mission Control.
- No HubSpot batch apply path changes.
- No Instantly send/enrollment execution.
- No paid skiptrace or live tax/land-record calls.
