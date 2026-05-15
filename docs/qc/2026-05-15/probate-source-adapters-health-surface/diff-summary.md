# Diff summary

## Added

- `app/services/probate_source_adapter_service.py`
  - New read-only Harris/Montgomery probate export adapter contract.
  - Normalizes county export column aliases into canonical source rows.
  - Adds deterministic source-row IDs and adapter/version metadata.

## Updated

- `app/services/probate_source_file_service.py`
  - Adds `build_nightly_payload_from_files` for multi-file source packets.
  - Uses the adapter service before placing rows into `metadata.source_rows`.
  - Adds `source_files`, `source_uris`, and `source_adapter_contract` metadata.

- `scripts/probate_source_file_payload.py`
  - `--source-file` is repeatable for Harris+Montgomery export packets.

- `app/services/probate_autopilot_manifest_service.py`
  - Detects duplicate case numbers in normalized rows.
  - Writes a duplicate-case artifact while preserving no-send metadata.

- `app/services/nightly_lead_machine_service.py`
  - Adds duplicate-case aggregate source quality and anomalies.
  - Adds safe source-request metadata allowlist instead of raw request metadata.
  - Adds read-only probate autopilot health report builder.
  - Rejects boolean metadata counts when aggregating numeric brief fields.

- `scripts/probate_autopilot_doctor.py`
  - Adds optional freshness SLA gate via `--max-brief-age-hours`.

- `app/models/source_runs.py`
  - Adds `ProbateAutopilotHealthResponse`.

- `app/api/mission_control.py`
  - Adds `GET /mission-control/probate-autopilot/health`.

- `apps/mission-control/src/lib/api.ts`
  - Adds typed API client method for the probate autopilot health endpoint.

- `apps/mission-control/src/lib/api.test.ts`
  - Covers health endpoint client URL and query parameter mapping.

- Python tests updated across:
  - `tests/services/test_probate_source_file_service.py`
  - `tests/scripts/test_probate_source_file_payload.py`
  - `tests/services/test_nightly_lead_machine_service.py`
  - `tests/scripts/test_probate_autopilot_doctor.py`
  - `tests/api/test_nightly_lead_machine.py`

## Explicitly not changed

- No live county scraping.
- No HubSpot write path.
- No Instantly enrollment/send path.
- No Vapi/SMS/direct-mail/skiptrace side effect.
- No provider live gate was opened.
