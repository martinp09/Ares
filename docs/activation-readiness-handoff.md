# Ares Activation Readiness Handoff

Status: current
Last verified: 2026-05-10
Repo: `martinp09/Ares`
Runtime merge baseline: `origin/main` after PR #7 (`cda9c828de40f9738bf936b185685ff47e5aac26`)

## Goal

Move the merged lease-options intake work from code-ready to live-operational without leaking secrets, bypassing approval gates, or turning on provider sends accidentally.

## Current Bottom Line

- The backend code is merged and verified.
- The first deploy can stay safe with `PROVIDER_LIVE_SENDS_ENABLED=false`.
- Live delivery is still blocked by provider/account/env setup, not by missing Ares code.
- Run `python scripts/activation_readiness.py --json` before any live smoke. It reports missing gates without printing raw secrets.
- If the existing VPS env file is available, run the env-file variant below to reuse known local credentials without copying secrets into this checkout:

```bash
python scripts/activation_readiness.py --json \
  --env-file /opt/ares/Ares/.env \
  --runtime-url https://production-readiness-afternoon.vercel.app \
  --derive-local-defaults
```

## Required Ares Runtime Env

Runtime/auth:

```bash
RUNTIME_API_KEY=<server-runtime-bearer-token>
RUNTIME_DOCS_ENABLED=false
RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED=false
PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true
PROVIDER_LIVE_SENDS_ENABLED=false # keep false until approved smoke/live launch
```

TextGrid:

```bash
TEXTGRID_ACCOUNT_SID=<textgrid-account-sid>
TEXTGRID_AUTH_TOKEN=<textgrid-auth-token>
TEXTGRID_FROM_NUMBER=<e164-sender-number>
TEXTGRID_WEBHOOK_SECRET=<textgrid-webhook-secret>
TEXTGRID_STATUS_CALLBACK_URL=https://<ares-runtime>/marketing/webhooks/textgrid
```

Resend:

```bash
RESEND_API_KEY=<resend-api-key>
RESEND_FROM_EMAIL="Name <verified@yourdomain.com>"
RESEND_REPLY_TO_EMAIL=<reply-to-email>
```

Slack:

```bash
SLACK_BOT_TOKEN=<xoxb-token>
SLACK_CHANNEL_INTAKE=<channel-id>
# Optional fallback / ops channels
SLACK_CHANNEL_LEADS=<channel-id>
SLACK_CHANNEL_ERRORS=<channel-id>
```

Cal.com / Trigger:

```bash
CAL_BOOKING_URL=https://cal.com/<seller-review-route>
CAL_WEBHOOK_SECRET=<cal-webhook-secret>
TRIGGER_SECRET_KEY=<trigger-secret-key>
TRIGGER_API_URL=https://api.trigger.dev
TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking
TRIGGER_APPOINTMENT_REMINDER_TASK_ID=marketing-send-appointment-reminder
MARKETING_APPOINTMENT_REMINDERS_ENABLED=true
```

## Required Landing Env

Set these in the landing deployment target, not browser code:

```bash
BUSINESS_RUNTIME_MARKETING_LEADS_URL=https://<ares-runtime>/marketing/leads
BUSINESS_RUNTIME_API_KEY=<same-value-as-Ares-RUNTIME_API_KEY>
BUSINESS_RUNTIME_BUSINESS_ID=limitless
BUSINESS_RUNTIME_ENVIRONMENT=prod
BUSINESS_RUNTIME_SITE_EVENTS_URL=https://<ares-runtime>/site-events
```

## External Dashboard Checks

Before live launch, check provider dashboards for old callback URLs that include query-string secrets such as `runtime_api_key`, `api_key`, `token`, or `secret`.

Check at least:

- TextGrid status callback
- Cal.com webhook URL
- Instantly webhook URL
- Trigger runtime callback/env URLs
- Landing hosting envs

Ares should receive provider callbacks through signed/provider-authenticated routes and server-side bearer auth where appropriate. Do not put runtime bearer tokens in URLs.

## Smoke Sequence

1. Safe readiness report, no provider sends:

```bash
python scripts/activation_readiness.py --json
python scripts/activation_readiness.py --json \
  --env-file /opt/ares/Ares/.env \
  --runtime-url https://production-readiness-afternoon.vercel.app \
  --derive-local-defaults
python scripts/smoke_provider_readiness.py
```

2. Hosted deploy smoke with live sends still disabled:

```bash
PROVIDER_LIVE_SENDS_ENABLED=false
# submit landing form or POST directly to /marketing/leads with approved test payload
# confirm side_effects are skipped or queued only where safe
```

3. Approved live smoke only after Martin approves recipient(s):

```bash
PROVIDER_LIVE_SENDS_ENABLED=true
python scripts/activation_readiness.py --json
# then use Ares routes, not direct provider scripts:
# GET /mission-control/providers/status
# POST /mission-control/outbound/sms/test
# POST /mission-control/outbound/email/test
# POST /marketing/leads with approved test lead
```

## Expected Remaining Blockers From Local Readiness Run

Captured at `docs/qc/2026-05-10/activation-readiness-handoff/activation-readiness-output.json` before loading the VPS env file:

- `PROVIDER_LIVE_SENDS_ENABLED=false` safe default blocks live delivery.
- Local `/root/Ares-inspect` env is missing TextGrid/Resend/Slack/Cal/Trigger live settings.
- Landing runtime env is not present in this shell, so hosted envs still need to be set/verified externally.

After loading `/opt/ares/Ares/.env` with `--derive-local-defaults`, the locally fixable gates shrink to these remaining blockers:

- `PROVIDER_LIVE_SENDS_ENABLED=false` remains the safe default until the final approved live smoke.
- `RESEND_FROM_EMAIL` is present but invalid; set it to a verified sender identity.
- `SLACK_BOT_TOKEN` is missing.
- `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` is missing.
- `CAL_WEBHOOK_SECRET` is missing and must match the external Cal.com webhook configuration.
- Hosted Ares still returned `401 Unauthorized` for protected Mission Control routes with the local runtime key, so Vercel/production env access is required to verify or update the deployed `RUNTIME_API_KEY`/landing envs.

## Do Not Claim Until Proven

Do not claim SMS/email/Slack delivery until the provider route response proves a provider request left Ares and a final provider status or callback proves delivery. Known provider gates/lessons:

- TextGrid: account balance blocker cleared after funding, but an initially `queued` message can later fail as `Blocked by Textgrid Content Filter`; poll TextGrid status or consume callbacks before claiming delivery.
- TextGrid SMS copy: keep intake SMS confirmation-only/no booking link; the landing page handles the Cal.com redirect and email can carry the booking-link fallback.
- Resend: `RESEND_FROM_EMAIL` was not a valid verified sender identity.
- Slack: bot token/channel not present.
