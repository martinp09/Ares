# Diff Summary — Probate Source File Adapter + Operator Health

## Working tree status before staging/commit

```text
 M app/services/nightly_lead_machine_service.py
 M tests/services/test_nightly_lead_machine_service.py
?? app/services/probate_source_file_service.py
?? docs/qc/2026-05-15/probate-source-file-adapter-operator-health/
?? scripts/probate_source_file_payload.py
?? tests/scripts/test_probate_source_file_payload.py
?? tests/services/test_probate_source_file_service.py
```

## Changed files

- Modify: `app/services/nightly_lead_machine_service.py`
  - Added `sla_health` and `source_anomalies` morning-brief sections.
  - Added expected-county detection, missing-county anomalies, source-count mismatch anomalies, invalid-row-rate anomalies, zero-parse-yield anomalies, and SLA status calculation.
  - Kept `outbound_allowed: false` in SLA output.
- Create: `app/services/probate_source_file_service.py`
  - Added CSV/JSON/JSONL source-file loader and no-send nightly-payload builder.
  - Groups Harris/Montgomery rows, emits explicit expected counties, and rejects malformed rows/county gaps.
- Create: `scripts/probate_source_file_payload.py`
  - CLI to build a no-send payload from a local probate source export.
  - Supports stdout and output-file modes.
- Modify: `tests/services/test_nightly_lead_machine_service.py`
  - Added SLA/anomaly tests for source-count mismatch and missing expected county.
- Create: `tests/services/test_probate_source_file_service.py`
  - Added parser, payload, adapter-path SLA, and no-provider-side-effect tests.
- Create: `tests/scripts/test_probate_source_file_payload.py`
  - Added CLI output-file, stdout-from-any-cwd, and invalid-run-kind tests.
- Create: `docs/qc/2026-05-15/probate-source-file-adapter-operator-health/`
  - Added this QC bundle.

## Diff stat before staging

```text
 app/services/nightly_lead_machine_service.py       | 144 +++++++++++++++++++++
 .../services/test_nightly_lead_machine_service.py  |  30 +++++
 2 files changed, 174 insertions(+)
```

Untracked files are listed above; they are intentionally part of this slice and are staged in the commit.
