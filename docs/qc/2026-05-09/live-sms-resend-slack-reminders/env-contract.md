# Env contract — live SMS / Resend / Slack / reminders

## Safe default

```bash
PROVIDER_LIVE_SENDS_ENABLED=false
```

Live sends should only be enabled for approved recipients and after provider readiness checks pass.

## Ares runtime

```bash
RUNTIME_API_KEY=<runtime-api-key>
PROVIDER_LIVE_SENDS_ENABLED=true
CAL_BOOKING_URL=<seller-review-booking-url>
CAL_WEBHOOK_SECRET=<cal-webhook-secret>
```

## TextGrid SMS

```bash
TEXTGRID_ACCOUNT_SID=<account-sid>
TEXTGRID_AUTH_TOKEN=<auth-token>
TEXTGRID_FROM_NUMBER=<approved-e164-sender>
TEXTGRID_STATUS_CALLBACK_URL=https://<ares-runtime>/marketing/webhooks/textgrid
TEXTGRID_WEBHOOK_SECRET=<textgrid-webhook-secret>
```

Notes:
- TextGrid numbers are normalized to E.164 in both lead-intake SMS and Mission Control test sends.
- The approved local smoke recipient was Martin at `+1***5914`.
- Latest route smoke reached TextGrid but TextGrid returned: `Balance is below 0. Please Add Funds and try again`.

## Resend email

```bash
RESEND_API_KEY=<api-key>
RESEND_FROM_EMAIL="Name <verified@domain.com>"
RESEND_REPLY_TO_EMAIL=<reply-to-email>
```

Notes:
- `RESEND_FROM_EMAIL` must be a valid sender identity (`email@example.com` or `Name <email@example.com>`).
- The provider status path now marks invalid sender identity as `configured=false`.
- Latest route smoke did not send email because local `RESEND_FROM_EMAIL` is invalid.

## Slack intake alert

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_INTAKE=C...
# fallback if intake is unset
SLACK_CHANNEL_LEADS=C...
```

Notes:
- Slack is server-side `chat.postMessage` only.
- Missing Slack config skips safely and does not block lead intake.

## Trigger appointment reminders

```bash
TRIGGER_SECRET_KEY=<trigger-secret>
TRIGGER_API_URL=https://api.trigger.dev
TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking
TRIGGER_APPOINTMENT_REMINDER_TASK_ID=marketing-send-appointment-reminder
MARKETING_APPOINTMENT_REMINDERS_ENABLED=true
```

Reminder scheduling additionally requires `PROVIDER_LIVE_SENDS_ENABLED=true` and a valid Cal.com `starts_at` in the booking webhook.
