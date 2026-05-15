# Diff Summary — Probate Autopilot Source Foundation

## Working tree status before staging/commit

```text
 M CONTEXT.md
 M TODO.md
 M app/models/source_runs.py
 M app/services/nightly_lead_machine_service.py
 M memory.md
 M tests/api/test_nightly_lead_machine.py
 M tests/api/test_trigger_contract_files.py
 M tests/services/test_nightly_lead_machine_service.py
 M trigger/src/lead-machine/runtime.ts
?? app/services/probate_autopilot_manifest_service.py
?? docs/qc/2026-05-15/
?? trigger/src/lead-machine/probateAutopilotSchedules.ts
```

## Tracked-file diff status

```text
M	CONTEXT.md
M	TODO.md
M	app/models/source_runs.py
M	app/services/nightly_lead_machine_service.py
M	memory.md
M	tests/api/test_nightly_lead_machine.py
M	tests/api/test_trigger_contract_files.py
M	tests/services/test_nightly_lead_machine_service.py
M	trigger/src/lead-machine/runtime.ts
```

## Untracked/new files

```text
app/services/probate_autopilot_manifest_service.py
docs/qc/2026-05-15/probate-autopilot-source-foundation/REPORT.md
docs/qc/2026-05-15/probate-autopilot-source-foundation/diff-summary.md
docs/qc/2026-05-15/probate-autopilot-source-foundation/test-output.txt
trigger/src/lead-machine/probateAutopilotSchedules.ts
```

## What changed and why

- Modify: `app/models/source_runs.py` — added Montgomery/PRD source lanes and first-class source-run fields for county, run kind, idempotency, raw/parsed/source-reported/keep-now counts.
- Modify: `app/services/nightly_lead_machine_service.py` — recognizes probate-autopilot requests, builds Harris+Montgomery no-send manifests, carries PRD fields into source runs, and expands morning brief sections.
- Create: `app/services/probate_autopilot_manifest_service.py` — Phase 1 no-live/no-send Harris+Montgomery manifest builder. It now rejects boolean count values and uses Trigger-provided `window_end` metadata for audit-useful source keys.
- Modify: `tests/services/test_nightly_lead_machine_service.py` — coverage for autopilot manifests, Montgomery lane acceptance, no-send confirmation, keep-now counts, source-count mismatch detection, and boolean-count rejection.
- Modify: `tests/api/test_nightly_lead_machine.py` — API coverage for Montgomery lane filtering and autopilot no-send source runs.
- Modify: `tests/api/test_trigger_contract_files.py` — contract checks for the scheduled Trigger cadence, no-send metadata, and scheduled `window_end` propagation.
- Modify: `trigger/src/lead-machine/runtime.ts` — extended Trigger payload/response types for PRD source lanes and source-run fields.
- Create: `trigger/src/lead-machine/probateAutopilotSchedules.ts` — scheduled no-send Trigger wrappers for 07:10, 12:40, 17:40, 02:20 CT and Sunday 03:15 CT.
- Modify: `CONTEXT.md`, `TODO.md`, `memory.md` — living-doc handoff updated with exact branch, QC path, safety boundaries, and next gates.
- Create/update: `docs/qc/2026-05-15/probate-autopilot-source-foundation/` — durable QC report, captured test output, and this diff summary.

## Tracked diff stat

```text
 CONTEXT.md                                         |   8 +-
 TODO.md                                            |  21 +++--
 app/models/source_runs.py                          |  39 ++++++++
 app/services/nightly_lead_machine_service.py       |  99 +++++++++++++++++++-
 memory.md                                          |  27 +++---
 tests/api/test_nightly_lead_machine.py             |  52 +++++++++++
 tests/api/test_trigger_contract_files.py           |  19 ++++
 .../services/test_nightly_lead_machine_service.py  | 101 +++++++++++++++++++++
 trigger/src/lead-machine/runtime.ts                |  45 ++++++++-
 9 files changed, 384 insertions(+), 27 deletions(-)
```

Note: untracked/new files are listed separately above because `git diff --stat` excludes them until staged.
