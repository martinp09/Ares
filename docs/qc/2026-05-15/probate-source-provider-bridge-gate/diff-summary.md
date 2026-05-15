# Diff Summary

## Added

- `app/services/probate_source_provider_service.py`
  - Disabled-by-default bridge for Harris/Montgomery probate source-provider intent.
  - Supports `source_provider_bridge.mode = local_export_files` only.
  - Reads local CSV/JSON/JSONL export files through existing parser contracts.
  - Hydrates existing `source_rows` metadata for the durable source-run/artifact pipeline.
  - Rejects `live_source_calls` unless the env gate and explicit approval exist, and still has no registered live adapters.

- `tests/services/test_probate_source_provider_service.py`
  - Covers local export hydration.
  - Covers live-source rejection before work.
  - Covers nightly service bridge execution without live calls.
  - Covers unsupported mode rejection.

- `docs/qc/2026-05-15/probate-source-provider-bridge-gate/`
  - QC report, diff summary, and command output evidence.

## Updated

- `app/core/config.py`
  - Added `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED`, default `false`.

- `app/services/nightly_lead_machine_service.py`
  - Delegates live-source rejection to the provider bridge.
  - Hydrates source-provider bridge metadata before building probate autopilot manifests.

- `app/services/probate_autopilot_manifest_service.py`
  - Carries safe source-provider bridge metadata into source-run metadata.
  - Keeps raw rows/case details in internal artifacts/metadata, not public Mission Control health summaries.

## Not Changed

- No live county scraper/browser/API adapter registered.
- No HubSpot, Instantly, SMS, Vapi, Slack, direct-mail, or skiptrace mutation paths.
- No Trigger schedule behavior changes.
- No public health/panel raw-row exposure.
