# Diff Summary

## Trigger schedule safety

- Added `trigger/src/shared/scheduleGate.ts` with `ARES_TRIGGER_SCHEDULES_ENABLED` default-false schedule gate.
- Updated `trigger/src/lead-machine/probateAutopilotSchedules.ts` so Harris/Montgomery probate schedules return a skipped/no-op response unless the gate is true.
- Updated `trigger/src/marketing/smsReplyAgentProcessor.ts` so the every-minute SMS reply-agent processor returns a skipped/no-op response unless the gate is true.

## Contracts and docs

- Updated `.env.example` with `ARES_TRIGGER_SCHEDULES_ENABLED=false` and an explicit activation note.
- Updated `tests/api/test_trigger_contract_files.py` to assert schedule gate wiring exists.
- Updated `CONTEXT.md`, `TODO.md`, and `memory.md` to reflect Trigger auth recovery, guarded Trigger prod `20260516.2`, stale Vercel runtime target, and Hermes cron remaining authoritative.
- Added this QC folder with report, test output, and diff summary.

## Operational state

- Trigger CLI auth is available in Hermes HOME.
- Trigger prod is deployed but guarded.
- Hermes cron `815e1261ab2e` is active.
- No outbound/provider-send gates were opened.
