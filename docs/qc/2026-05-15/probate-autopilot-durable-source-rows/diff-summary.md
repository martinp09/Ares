# Diff Summary — Probate Autopilot Durable Source Rows

## Working tree status before staging/commit

```text
 M app/core/config.py
 M app/db/source_runs.py
 M app/services/nightly_lead_machine_service.py
 M app/services/probate_autopilot_manifest_service.py
 M tests/services/test_nightly_lead_machine_service.py
?? docs/qc/2026-05-15/probate-autopilot-durable-source-rows/
```

## What changed and why

- Modify: `app/core/config.py`
  - Added `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` for optional durable local source-run state.
  - Added `LEAD_MACHINE_ARTIFACT_ROOT` for optional raw/normalized/keep-now artifact persistence.
- Modify: `app/db/source_runs.py`
  - Added file-backed source-run repository state with file lock, reload-before-save, atomic replace, and domain corruption errors.
  - Persisted source runs, briefs, and idempotency maps when a state path is configured.
- Modify: `app/services/probate_autopilot_manifest_service.py`
  - Added `source_rows` ingestion for Harris and Montgomery.
  - Added source-row normalization, invalid-row dead-letter artifacts, keep-now artifact generation, checksums, and artifact-root writes.
  - Preserved no-send/provider-disabled metadata.
- Modify: `app/services/nightly_lead_machine_service.py`
  - Passed configured artifact root into the autopilot manifest builder.
  - Added `source_quality`, `enrichment_backlog`, and `operator_next_actions` morning-brief sections.
- Modify: `tests/services/test_nightly_lead_machine_service.py`
  - Added tests for restart idempotency replay, reload-before-save multi-writer preservation, corrupt state errors, source-row artifact writes, source-count mismatches, and operator-next-action sections.
- Create: `docs/qc/2026-05-15/probate-autopilot-durable-source-rows/`
  - Added this QC bundle.

## Diff stat

```text
 app/core/config.py                                 |   8 +
 app/db/source_runs.py                              | 157 +++++++--
 app/services/nightly_lead_machine_service.py       |  88 ++++-
 app/services/probate_autopilot_manifest_service.py | 362 ++++++++++++++++++---
 .../services/test_nightly_lead_machine_service.py  | 165 +++++++++-
 5 files changed, 697 insertions(+), 83 deletions(-)
```
