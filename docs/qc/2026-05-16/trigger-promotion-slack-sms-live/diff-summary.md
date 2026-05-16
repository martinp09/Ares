# Diff Summary — Trigger promotion / Slack + SMS readiness

Generated: 2026-05-16T21:15:28Z

## Intentional changes

- Trigger schedule code now exports exactly three Harris/Montgomery probate lead-run schedules in America/Chicago: 07:10, 12:40, and 17:40.
- Retired 02:20 daily reconciliation and Sunday 03:15 weekly reconciliation schedules were removed from the deployed worker contract.
- Tests assert the three-times-per-day cadence and absence of retired reconciliation schedules.
- Runbook, CONTEXT, TODO, memory, and QC index now reflect Trigger scheduler authority, Hermes cron pause, Slack route delivery, and SMS readiness gates.
- QC artifacts capture sanitized Trigger deploy/env/worker, runtime smokes, Slack/SMS readiness, cron handoff, tests, and final verification.

## Git diff stat
```text
 CONTEXT.md                                         | 24 +++++++++++----------
 TODO.md                                            | 13 +++++------
 docs/qc/2026-05-16/README.md                       |  5 +++--
 ...tgomery-probate-autopilot-no-send-activation.md | 22 +++++++++++--------
 memory.md                                          | 25 ++++++++++++++--------
 tests/api/test_trigger_contract_files.py           | 10 +++++----
 .../src/lead-machine/probateAutopilotSchedules.ts  | 22 +------------------
 7 files changed, 59 insertions(+), 62 deletions(-)
```

## Git status including new QC files
```text
 M CONTEXT.md
 M TODO.md
 M docs/qc/2026-05-16/README.md
 M docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md
 M memory.md
 M tests/api/test_trigger_contract_files.py
 M trigger/src/lead-machine/probateAutopilotSchedules.ts
?? docs/qc/2026-05-16/trigger-promotion-slack-sms-live/
```

## Changed tracked files
```text
M	CONTEXT.md
M	TODO.md
M	docs/qc/2026-05-16/README.md
M	docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md
M	memory.md
M	tests/api/test_trigger_contract_files.py
M	trigger/src/lead-machine/probateAutopilotSchedules.ts
```
