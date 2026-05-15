# Diff Summary — Probate Autopilot Doctor

## Working tree status before staging/commit

```text
?? docs/qc/2026-05-15/probate-autopilot-doctor/
?? scripts/probate_autopilot_doctor.py
?? tests/scripts/test_probate_autopilot_doctor.py
```

## Changed files

- Create: `scripts/probate_autopilot_doctor.py`
  - Read-only health reporter for the file-backed source-run ledger.
  - Emits JSON for latest brief SLA, anomalies, no-send posture, backlog, and operator next actions.
  - Supports `--fail-on-blocked` for watchdog wrappers.
- Create: `tests/scripts/test_probate_autopilot_doctor.py`
  - Covers blocked SLA, fail-on-blocked exit code, and no-data behavior.
- Create: `docs/qc/2026-05-15/probate-autopilot-doctor/`
  - Added this QC bundle.

## Diff stat before staging

No tracked-file diff before staging because this slice only adds new files.
