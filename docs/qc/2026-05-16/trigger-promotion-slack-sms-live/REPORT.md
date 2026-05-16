# Trigger Promotion + Slack/SMS Readiness QC

Generated: 2026-05-16T21:05:22Z

## Scope

Promote Ares Harris/Montgomery probate lead-machine schedule authority from Hermes cron to Trigger.dev, verify exactly three Central Time lead runs per day, verify Slack delivery routes, and verify SMS/TextGrid runtime readiness without enabling outbound campaign sends or automatic SMS replies.

## Results

- Trigger prod worker version: `20260516.4`.
- Trigger probate schedule tasks: `harris-montgomery-probate-0710-ct, harris-montgomery-probate-1240-ct, harris-montgomery-probate-1740-ct`.
- Retired reconciliation schedules present: `False`.
- Trigger schedule gate: `true`.
- Trigger runtime base URL: `https://ares.tail485fd9.ts.net`.
- Controlled lead-machine Trigger run: `run_cmp8tvbii55lq0hmz6qca6n5i` completed.
- Controlled SMS processor Trigger run: `run_cmp8tyk826wnf0vojep91id9s` completed.
- Runtime probate health: `healthy` with no-send `True` and outbound allowed `False`.
- Latest brief after controlled Trigger run: `morning_brief_f27f1679d1884a149cf5f3d53fc09f76`, new records `0`, hot leads `0`.
- Slack persisted attempts: `2`; recent attempts include the lead-run digest and controlled hot-leads routing test with Slack message timestamps.
- SMS provider readiness: TextGrid configured; `/sms-agent/internal/process-pending` returns zero sends; unsigned malformed public webhook is rejected; outbound provider sends and auto-replies remain intentionally disabled.

## Commands / checks captured

- `uv run pytest -q tests/api/test_trigger_contract_files.py tests/services/test_slack_notification_service.py tests/scripts/test_slack_notification_readiness.py`
- `npm --prefix trigger run typecheck`
- `git diff --check`
- Trigger API sanitized worker/env inspection.
- Funnel API public/protected smoke checks.
- Slack persisted notification attempt inspection.
- SMS provider/status, pending-processor, and webhook signature smoke checks.

## Artifacts

- `test-output.txt` — focused tests, Trigger typecheck, diff check.
- `trigger-deploy-output-sanitized.txt` — sanitized Trigger prod deploy evidence for worker `20260516.4`.
- `trigger-worker-env-output.json` — sanitized Trigger worker/env/scheduled-task evidence.
- `runtime-smoke-output.json` — Funnel runtime, probate health, latest brief, source runs, provider, SMS route smoke.
- `slack-sms-readiness-output.json` — Slack notification attempt and SMS readiness summary.
- `diff-summary.md` — changed-file intent.
- `final-verification.txt` — concise final verification snapshot.
- `cron-handoff-output.json` — Hermes cron pause evidence and rollback note.

## Scheduler handoff

- Hermes no-agent cron `815e1261ab2e` is paused; Trigger is scheduler authority unless intentionally rolled back.
- Trigger prod worker `20260516.4` owns the 07:10, 12:40, and 17:40 America/Chicago probate lead-run windows.

## Safety posture

- Provider campaign sends were not enabled.
- SMS automatic replies remain disabled (`SMS_AGENT_MODE=draft_only`, `SMS_AGENT_AUTO_REPLIES_ENABLED=false`).
- Global provider send gate remains false in the live runtime.
- Trigger promotion is scheduler authority only, not approval to enroll/send outreach.
