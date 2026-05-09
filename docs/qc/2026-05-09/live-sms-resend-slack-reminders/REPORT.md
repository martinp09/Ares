# Report — live SMS / Resend / Slack / appointment reminders

Date: 2026-05-09
Repo: `martinp09/Ares`
Branch: `feat/landing-ares-intake-sms-agent`

## Scope

Finish the production-readiness pass for the lease-option intake notification bundle:

- TextGrid confirmation SMS with normalized numbers, booking link, and STOP copy.
- Resend confirmation email with the same booking link.
- Slack intake alert scaffold for speed-to-lead operator notification.
- Cal.com appointment reminder scheduling and dispatch by SMS/email.
- Safe live-send gating and provider-readiness evidence.

## What changed

- Added/finished SMS/email/Slack lead-intake side effects in `MarketingLeadService`.
- Added phone normalization to TextGrid request builders used by intake and Mission Control test sends.
- Added appointment `starts_at`, reminder scheduler, reminder dispatch endpoint, and Trigger task.
- Added Resend sender validation so invalid local `RESEND_FROM_EMAIL` is not reported as send-ready.
- Added tests covering the new provider bundle and appointment reminder behavior.
- Updated README/TODO/CONTEXT/memory with the current env contract and live-smoke blockers.

## Live smoke

Approved recipient:

- SMS: Martin at `+1***5914`
- Email: Martin's provided email, redacted in artifacts

Routes hit through Ares with `PROVIDER_LIVE_SENDS_ENABLED=true` in-process and memory-backed local state:

- `GET /mission-control/providers/status` → `200`
- `POST /mission-control/outbound/sms/test` → `502`, provider returned `Balance is below 0. Please Add Funds and try again`
- `POST /mission-control/outbound/email/test` → `502`, Ares rejected invalid `RESEND_FROM_EMAIL` before provider send

Conclusion: route/provider wiring is present, but live delivery is still blocked by provider account/env state. No delivery is claimed.

## Verification commands

Captured in this QC folder:

- Focused tests: `uv run pytest tests/services/test_marketing_provider_notifications.py tests/api/test_marketing_leads.py tests/api/test_marketing_webhooks.py tests/services/test_booking_service.py tests/api/test_trigger_contract_files.py tests/providers/test_textgrid.py tests/providers/test_resend.py -q`
- Full backend tests: `uv run pytest -q`
- Trigger typecheck: `npm --prefix trigger run typecheck`
- Diff checks: `git diff --check` and `git diff --cached --check`

## Remaining gates

- Add/fund TextGrid account balance or resolve sender/account state.
- Set a verified `RESEND_FROM_EMAIL` sender identity.
- Add `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS`.
- Set `CAL_BOOKING_URL` and Cal webhook env before end-to-end appointment reminder smoke.
- Deploy/update landing envs and run hosted smoke only after the env contract is intentionally set.
