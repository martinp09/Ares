# Ares Chief of Staff Trigger Check-In QC Report

Date: 2026-05-18
Branch: `feature/ares-chief-of-staff-v0`
Worktree: `/opt/ares/worktrees/ares-chief-of-staff-v0`

## Scope

Continued the Ares Chief of Staff PRD after the Mission Control dashboard update by turning the Slack-first employee report into a runtime-schedulable employee check-in.

Implemented:

- Protected runtime endpoint: `POST /ares-chief-of-staff/internal/check-in`.
- Trigger-safe response contract: `ares_chief_of_staff_check_in_v1`.
- Explicit read-only request flags:
  - `no_send=true`
  - `provider_sends_enabled=false`
  - `live_source_calls=false`
  - `live_provider_writes=false`
  - `outreach_allowed=false`
- Default-safe Slack delivery gate: `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false`.
- Trigger manual task: `chief-of-staff-check-in`.
- Trigger daily schedule: `chief-of-staff-check-in-0815-ct`, `08:15 CT`, gated by `ARES_TRIGGER_SCHEDULES_ENABLED` and the separate Chief of Staff Slack gate.
- Trigger task response avoids raw lead PII by returning counts, queue summaries, action counts, safety booleans, artifact keys/paths, and redaction metadata only.

## Safety boundaries

This slice did **not** perform:

- seller outreach
- paid skiptrace
- Instantly enrollment/send
- HubSpot/provider writes
- SMS/email/Vapi sends
- live county/source pulls
- manager approval execution
- live Slack post
- Telegram delivery
- Supabase remote migration
- VPS deploy

Slack posting remains disabled unless all of these are true after deploy:

1. `SLACK_NOTIFICATIONS_ENABLED=true`
2. `SLACK_BOT_TOKEN` is configured
3. `SLACK_CHANNEL_CHIEF_OF_STAFF` is configured and bot is invited
4. request/schedule asks for `send_slack=true`
5. `ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=true`

## Verification

Commands run from `/opt/ares/worktrees/ares-chief-of-staff-v0`:

```bash
uv run pytest -q tests/api/test_ares_chief_of_staff_check_in.py tests/api/test_trigger_contract_files.py tests/api/test_runtime_config_contract.py tests/services/test_ares_chief_of_staff_service.py tests/scripts/test_ares_chief_of_staff_digest.py tests/scripts/test_slack_notification_readiness.py tests/services/test_slack_notification_service.py tests/db/test_slack_notifications_repository.py tests/db/test_leads_repository.py
npm --prefix trigger run typecheck
RUNTIME_API_KEY=dev-runtime-key CONTROL_PLANE_BACKEND=memory MARKETING_BACKEND=memory LEAD_MACHINE_BACKEND=memory SITE_EVENTS_BACKEND=memory SLACK_NOTIFICATIONS_ENABLED=false ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false uv run python <api smoke>
uv run pytest -q
```

Results:

- Focused Chief of Staff / Slack / Trigger contract suite: `61 passed`.
- Trigger TypeScript typecheck: passed.
- Protected API smoke: `200`, `no_send=true`, `slack_notification.status=blocked_by_chief_of_staff_slack_gate`, response redaction `counts_only_no_lead_pii`.
- Full backend test suite: `1148 passed`.

## Evidence files

- `focused-test-output.txt`
- `trigger-typecheck-output.txt`
- `api-check-in-smoke.json`
- `full-backend-test-output.txt`
- `diff-summary.md`
- `git-diff-check.txt`

## Notes

The next high-leverage employee feature remains the Slack reply inbox / decision journal for `approve cos_action_...` and `deny cos_action_...`. That should record manager intent only and must **not** call the generic approval executor until a separately approved command receiver and safety contract exist.
