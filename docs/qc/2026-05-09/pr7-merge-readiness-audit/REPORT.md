# PR #7 Merge Readiness Audit

Date: 2026-05-09
Repo: `martinp09/Ares`
Branch: `feat/landing-ares-intake-sms-agent`
PR: https://github.com/martinp09/Ares/pull/7

## Scope

Martin asked to merge the landing -> Ares intake/provider/reminder implementation if ready, or re-audit and finish anything still needed.

This pass rechecked PR #7 before merge and found two readiness blockers:

1. Slack intake alerts were configurable without also honoring the global `PROVIDER_LIVE_SENDS_ENABLED` send gate.
2. Cal.com `rescheduled` events for already-booked leads did not schedule/update appointment reminders because scheduling lived only inside the `newly_booked` branch.

## Fixes Applied

- `app/services/marketing_lead_service.py`
  - `_build_operator_notifier()` now returns the no-op notifier unless `PROVIDER_LIVE_SENDS_ENABLED=true`.
  - This keeps Slack operator alerts aligned with the global live-provider gate, not just token/channel presence.

- `app/services/booking_service.py`
  - Appointment reminder scheduling now runs for non-deduped `booked` and `rescheduled` events when a lead exists.
  - Initial booking confirmations still only send on newly booked events.
  - Rescheduled events suppress the non-booker sequence and refresh reminder scheduling without sending a duplicate confirmation.

- Tests added:
  - `test_lead_intake_skips_slack_when_live_sends_are_disabled_even_if_configured`
  - `test_rescheduled_calcom_event_reschedules_reminders_without_new_confirmation`

## Verification

Commands run from `/root/Ares-inspect`:

```bash
uv run pytest tests/services/test_marketing_provider_notifications.py tests/services/test_booking_service.py -q
uv run pytest -q
npm --prefix trigger run typecheck
git diff --check
```

Results:

- Focused tests: `13 passed`
- Full backend tests: `648 passed`
- Trigger typecheck: passed
- Diff whitespace check: passed

Captured outputs:

- `focused-test-output.txt`
- `full-test-output.txt`
- `trigger-typecheck-output.txt`
- `diff-check.txt`
- `diff-summary.md`

## Remaining Non-Code Launch Gates

These remain expected provider/environment blockers and are not merge blockers:

- TextGrid account balance/funding must be fixed before live SMS delivery succeeds.
- `RESEND_FROM_EMAIL` must be a valid verified sender identity before live email delivery succeeds.
- Slack live alerts require `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS`, plus `PROVIDER_LIVE_SENDS_ENABLED=true`.
- Cal.com and Trigger runtime envs must be set before hosted live reminder delivery.

## Verdict

Ready to merge after this audit/fix pass, subject to GitHub mergeability and successful push of the fix commit.
