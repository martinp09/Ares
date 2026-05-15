# Diff Summary

## Changed files

- `app/services/probate_autopilot_manifest_service.py`
  - Added `collect_probate_autopilot_keep_now_rows()` so the scheduled source-pull can safely reuse normalized keep-now rows in memory for enrichment without putting raw rows into public summaries.

- `app/services/nightly_lead_machine_service.py`
  - Injects `ProbatePropertyTaxTitleEnrichmentService` into nightly source pulls.
  - Runs property/CAD, tax-overlay, and land-record/title-friction enrichment when probate-autopilot source rows include keep-now records.
  - Creates internal zero-count enrichment stage source-run manifests/artifacts for Harris and Montgomery so `new_record_count` remains source-row-only.
  - Updates morning brief `enrichment_backlog` from actual enrichment completion/pending counts.
  - Updates operator next actions to distinguish incomplete enrichment from ready-for-review enriched queues.

- `tests/services/test_nightly_lead_machine_service.py`
  - Updated backlog/action expectations now that nightly source pull executes enrichment.
  - Added regression coverage proving a source-row nightly run emits property/CAD, tax, and land/title enrichment lanes and artifacts with no provider sends.

- `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
  - Documents inline nightly enrichment wiring, local artifact inputs, generated enrichment lanes, and no-send/live-gate boundaries.

- `CONTEXT.md`, `TODO.md`, `memory.md`
  - Updated living handoff docs to point at this branch and QC evidence.

## Diff stat before final commit

```text
app/services/nightly_lead_machine_service.py       | 534 ++++++++++++++++++++-
app/services/probate_autopilot_manifest_service.py |  20 +
tests/services/test_nightly_lead_machine_service.py  | 127 ++++-
```

Additional docs/QC files were added after that stat.
