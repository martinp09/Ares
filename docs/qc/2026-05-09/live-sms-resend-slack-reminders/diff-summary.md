# Diff summary — live SMS / Resend / Slack / reminders

## Backend API/config

- `app/api/marketing.py`
  - Added `POST /marketing/internal/appointment-reminder` for Trigger-driven reminder dispatch.
- `app/core/config.py`
  - Added appointment reminder task/settings and `SLACK_CHANNEL_INTAKE`.
  - Removed the incorrect `RESEND_EMAIL_URL` alias from `resend_from_email`.
- `app/providers/textgrid.py`
  - Added E.164 phone normalization for TextGrid outbound request builder.
- `app/services/providers/textgrid.py`
  - Normalizes Mission Control test-send `To`/`From` numbers to E.164 before provider calls.
- `app/services/providers/resend.py`
  - Validates `RESEND_FROM_EMAIL` shape in provider status and test-send paths.

## Lead intake

- `app/services/marketing_lead_service.py`
  - Adds booking-link confirmation copy with STOP language.
  - Adds Slack operator notification scaffold via `chat.postMessage`.
  - Returns side effects in order: SMS, email, Slack, non-booker Trigger check.

## Booking/reminders

- `app/services/booking_service.py`
  - Preserves Cal.com `starts_at`.
  - Adds reminder scheduler and dispatch path.
  - Sends/logs appointment reminders for booked/rescheduled leads.
  - Respects SMS consent for appointment confirmation/reminder SMS logs and sends.

## Trigger

- `trigger/src/marketing/sendAppointmentReminder.ts`
  - Adds `marketing-send-appointment-reminder` Trigger task that calls Ares `/marketing/internal/appointment-reminder`.

## Tests

- `tests/services/test_marketing_provider_notifications.py`
  - New focused coverage for SMS/email/Slack/reminders.
- `tests/api/test_marketing_leads.py`
  - Updated side-effect/copy expectations.
- `tests/api/test_marketing_webhooks.py`
  - Added appointment reminder endpoint coverage.
- `tests/api/test_trigger_contract_files.py`
  - Added Trigger task contract assertion.
- `tests/services/test_booking_service.py`
  - Updated SMS-consent-aware booking message expectations.
- `tests/providers/test_textgrid.py`
  - Added Mission Control TextGrid normalization coverage.
- `tests/providers/test_resend.py`
  - Added invalid sender identity status/send coverage.

## Docs/QC

- `README.md`, `TODO.md`, `CONTEXT.md`, `memory.md`
  - Updated live provider/reminder contract, current blockers, and handoff state.
- `docs/qc/2026-05-09/live-sms-resend-slack-reminders/`
  - Captures test, smoke, env, and diff evidence.
