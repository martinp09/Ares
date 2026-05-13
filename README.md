# Ares

Enterprise agent platform and deterministic business runtime for Hermes dogfood.

Agents are the product unit. Mission Control is the operator cockpit.

Hermes is the always-on shell.
This repo is the deterministic runtime, policy layer, orchestration surface, and system-of-record integration layer that Hermes controls.

## Core Principles

- Hermes handles interaction, approvals, and coordination.
- This repo handles typed commands, business policy, provider adapters, and execution wiring.
- `memory.md` is the master memory file.
- `CONTEXT.md` is the short router and TODO file. Keep it under 50 lines and point to exact sections in `memory.md`.
- `WAT_Architecture.md` defines the operating model for workflows, agents, and tools.
- Hermes <-> Ares setup/runbook: `docs/hermes-ares-integration-runbook.md`
- Full-stack local runbook: `docs/hermes-ares-trigger-supabase-runbook.md`
- Production-readiness handoff: `docs/production-readiness-handoff.md`
- Curative-title workflow wiki: `docs/curative-title-wiki/index.md`

## Initial Direction

- Generalist core first
- Industry packs second
- Real estate first
- Marketing control plane before seller-ops cutover

## Ares North Star

Ares is a self-hosted operating system for distressed real-estate lead management. It owns the data, automates the workflow, and surfaces only the decisions that require a human.

## Current Runtime Surface

- `GET /health`
- `POST /commands`
- `POST /approvals/{approval_id}/approve`
- `GET /runs/{run_id}`
- `POST /replays/{run_id}`
- `GET /hermes/tools`
- `POST /hermes/tools/{tool_name}/invoke`
- `POST /agents`
- `GET /agents/{agent_id}`
- `POST /agents/{agent_id}/revisions/{revision_id}/publish`
- `POST /agents/{agent_id}/revisions/{revision_id}/archive`
- `POST /agents/{agent_id}/revisions/{revision_id}/clone`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/events`
- `POST /permissions`
- `GET /permissions/{agent_revision_id}`
- `POST /outcomes`
- `POST /agent-assets`
- `GET /agent-assets/{asset_id}`
- `POST /agent-assets/{asset_id}/bind`
- `GET /mission-control/dashboard`
- `GET /mission-control/inbox`
- `GET /mission-control/runs`
- `POST /marketing/leads`
- `POST /marketing/webhooks/textgrid`
- `POST /marketing/webhooks/calcom`
- `POST /sms-agent/messages`
- `POST /sms-agent/webhooks/textgrid`
- `POST /voice/assistants`
- `POST /voice/phone-numbers`
- `POST /voice/calls/outbound`
- `POST /voice/vapi/webhook`
- `POST /site-events`
- `POST /trigger/callbacks/runs/{run_id}/started`
- `POST /trigger/callbacks/runs/{run_id}/completed`
- `POST /trigger/callbacks/runs/{run_id}/failed`
- `POST /trigger/callbacks/runs/{run_id}/artifacts`

Current implementation notes:

- FastAPI runtime supports memory-backed local development and Supabase-backed production persistence through repository seams under `app/db/`
- Trigger.dev marketing worker chain is deployed for production callbacks and remains the async host infrastructure, not the platform identity
- Trigger.dev is the current host infrastructure, not the platform identity
- Mission Control has native backend read models plus an `apps/mission-control/` cockpit
- Intake and provider flows are backed by deterministic Ares APIs; fixture paths remain for local/dev resilience only
- Mission Control UI now follows the approved dark industrial terminal / pixel CRT style system
- site-event ingestion is append-only and non-blocking at the API layer
- Production wiring is live for Supabase-backed runtime state, Trigger callbacks, Instantly reply webhooks, TextGrid SMS/status callbacks, Cal.com booking callbacks, and Resend email smoke. Evidence is in `docs/rollout-evidence/production-2026-04-25.json`.
- Lease-options landing-page contact intake is owned by Ares through `POST /marketing/leads`; the endpoint preserves seller-fit fields, consent metadata, and attribution from the public form, returns booking/side-effect status, and keeps seller-facing SMS/email plus Trigger reminder side effects gated by `PROVIDER_LIVE_SENDS_ENABLED`. Slack intake alerts are server-side and safely skipped until `PROVIDER_LIVE_SENDS_ENABLED=true` plus `SLACK_BOT_TOKEN` and an intake/lead channel are configured.
- Activation readiness handoff: `docs/activation-readiness-handoff.md`; non-secret gate report: `python scripts/activation_readiness.py --json`. When reusing the existing local VPS env without copying secrets, run `python scripts/activation_readiness.py --json --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults`.

## Landing Page Intake Contract

External seller forms should submit contact intake server-side to `POST /marketing/leads` with `Authorization: Bearer <RUNTIME_API_KEY>`. Do not expose runtime tokens in browser code or query strings.

Required request fields:

- `business_id`
- `environment`
- `first_name`
- `phone`
- `property_address`

Supported context fields:

- `last_name`, `email`, `property_type`
- `timeline_to_sell`, `monthly_payment_goal`, `asking_price_goal`
- `seller_goal`, `notes`
- `sms_consent`, `consent_page_url`, `consent_ip`, `consent_user_agent`
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `lp_var`

Response fields:

- `lead_id`
- `booking_status`
- `booking_url`
- `side_effects[]` with `name`, `status`, and optional `error_message`

Current side effects:

- `confirmation_sms`: TextGrid confirmation-only copy with STOP language and no booking link when `sms_consent=true`, TextGrid config exists, and `PROVIDER_LIVE_SENDS_ENABLED=true`.
- `confirmation_email`: Resend confirmation with the booking link fallback when Resend config exists and `PROVIDER_LIVE_SENDS_ENABLED=true`.
- `operator_slack_notification`: Slack `chat.postMessage` operator alert with lead/booking context when `PROVIDER_LIVE_SENDS_ENABLED=true` and `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` are configured; otherwise skipped safely.
- `trigger_non_booker_check`: delayed Trigger follow-up check when Trigger config exists and `PROVIDER_LIVE_SENDS_ENABLED=true`.

Appointment reminder flow:

- Cal.com booking webhooks now preserve `starts_at` when provided.
- Booked or rescheduled leads schedule Trigger reminder jobs for `24h` and `1h` before the appointment when `PROVIDER_LIVE_SENDS_ENABLED=true`, `MARKETING_APPOINTMENT_REMINDERS_ENABLED=true`, and `TRIGGER_SECRET_KEY` is set.
- Trigger task `marketing-send-appointment-reminder` calls `POST /marketing/internal/appointment-reminder` with bearer runtime auth.
- Reminder dispatch sends TextGrid SMS only for opted-in booked/rescheduled leads and sends Resend email when an email is present; both outbound message IDs are logged when providers return IDs.

Safe first deploy env:

```bash
RUNTIME_API_KEY=<runtime-api-key>
PROVIDER_LIVE_SENDS_ENABLED=false
CAL_BOOKING_URL=<seller-review-booking-url>
CAL_WEBHOOK_SECRET=<cal-webhook-secret>
TEXTGRID_ACCOUNT_SID=<set only for live SMS readiness>
TEXTGRID_AUTH_TOKEN=<set only for live SMS readiness>
TEXTGRID_FROM_NUMBER=<set only for live SMS readiness>
TEXTGRID_STATUS_CALLBACK_URL=https://<ares-runtime>/marketing/webhooks/textgrid
TEXTGRID_WEBHOOK_SECRET=<textgrid-webhook-secret>
RESEND_API_KEY=<set only for confirmation/reminder email readiness>
RESEND_FROM_EMAIL=<verified-sender>
RESEND_REPLY_TO_EMAIL=<reply-to-email>
SLACK_BOT_TOKEN=<set when Slack intake alerts are ready>
SLACK_CHANNEL_INTAKE=<slack-channel-id>
TRIGGER_SECRET_KEY=<trigger-secret-key>
TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking
TRIGGER_APPOINTMENT_REMINDER_TASK_ID=marketing-send-appointment-reminder
MARKETING_APPOINTMENT_REMINDERS_ENABLED=true
```

## Communication Agent Scaffold

Ares now has a deterministic provider substrate for broader communications automation, separate from the lease-options landing intake path:

- `POST /sms-agent/messages` sends or dry-runs a generic TextGrid SMS. With `PROVIDER_LIVE_SENDS_ENABLED=false` or `dry_run_only=true`, it returns `dry_run=true` and does not call TextGrid. When live sends are enabled and TextGrid is configured, it requires `contact_id` plus `sms_consent_confirmed=true`, normalizes `to`/`from` to E.164, calls TextGrid, and logs the outbound message.
- `POST /sms-agent/webhooks/textgrid` is a generic TextGrid webhook alias that reuses the existing inbound/status callback processor.
- `POST /voice/assistants`, `POST /voice/phone-numbers`, and `POST /voice/calls/outbound` scaffold Vapi assistant/number/call payloads. Vapi provider mutations and outbound calls stay dry-run unless both `PROVIDER_LIVE_SENDS_ENABLED=true` and `VAPI_PROVIDER_LIVE_SENDS_ENABLED=true` are set.
- `POST /voice/vapi/webhook` accepts Vapi Server URL messages, including `assistant-request`, `tool-calls`, `status-update`, `transcript`, and `end-of-call-report` shapes. Tool calls are wired into Mission Control context/tools: record search/detail, lane scripts, record updates, opportunity stage movement, task completion, lead qualification, follow-up summaries, and human handoff. The route is protected by the normal Ares runtime bearer auth; when `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true`, it also requires `X-Vapi-Secret: <VAPI_WEBHOOK_SECRET>`. Configure the Vapi Server URL credential/header before live callbacks.

Vapi envs:

```bash
VAPI_API_KEY=<vapi-api-key>
VAPI_BASE_URL=https://api.vapi.ai
VAPI_WEBHOOK_URL=https://<ares-runtime>/voice/vapi/webhook
VAPI_WEBHOOK_SECRET=<vapi-server-url-shared-secret>
VAPI_DEFAULT_ASSISTANT_ID=<optional-existing-assistant-id>
VAPI_DEFAULT_PHONE_NUMBER_ID=<optional-existing-phone-number-id>
VAPI_PROVIDER_LIVE_SENDS_ENABLED=false
VAPI_DEFAULT_MODEL_PROVIDER=openai
VAPI_DEFAULT_MODEL=gpt-4o
VAPI_DEFAULT_VOICE_PROVIDER=11labs
VAPI_DEFAULT_VOICE_ID=cgSgspJ2msm6clMCkdW9
```

## Local Runtime Contract

Default local development stays memory-backed unless a Supabase slice is intentionally enabled:

```bash
RUNTIME_API_BASE_URL=http://127.0.0.1:8000
RUNTIME_API_KEY=dev-runtime-key
CONTROL_PLANE_BACKEND=memory
MARKETING_BACKEND=memory
LEAD_MACHINE_BACKEND=memory
SITE_EVENTS_BACKEND=memory
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
VITE_RUNTIME_API_BASE_URL=
```

Startup:

```bash
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
RUNTIME_API_BASE_URL=http://127.0.0.1:8000 RUNTIME_API_KEY=dev-runtime-key npm --prefix apps/mission-control run dev -- --host 127.0.0.1 --port 5173
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000 HERMES_RUNTIME_API_KEY=dev-runtime-key npm --prefix trigger run dev
```

First smoke:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -H 'Authorization: Bearer dev-runtime-key' http://127.0.0.1:8000/hermes/tools
```

## Verification

- Activation gates: `python scripts/activation_readiness.py --json`
  - Existing local VPS env without copying secrets: `python scripts/activation_readiness.py --json --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults`
- Provider request shape: `python scripts/smoke_provider_readiness.py`
- Python: `uv run pytest -q`
- Lead machine smoke: `uv run python scripts/smoke/lead_machine_smoke.py`
- Trigger.dev: `npm --prefix trigger run typecheck`
- Mission Control: `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`

## Bootstrap

- `make dev` prints the local Ares / Mission Control / Trigger bootstrap commands.
- `make smoke` runs the lead machine smoke harness.

## Source of Truth

- `CONTEXT.md` for quick session routing
- `memory.md` for indexed master memory
- `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md` for the current cohesion integration scope
- `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md` for the accepted boundary gate
- `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md` for the merged phased Ares implementation sequence
- `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json` as the overnight loop handoff artifact
- future runtime database for canonical business state
- curative-title workflow wiki: `docs/curative-title-wiki/index.md`
- activation-readiness handoff: `docs/activation-readiness-handoff.md`
- production-readiness handoff for live wiring gates: `docs/production-readiness-handoff.md`
- production-readiness execution plan: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`

## Phase 1 Guardrails

- Counties remain fixed: Harris, Tarrant, Montgomery, Dallas, Travis
- Lead selection rule: land-record document/deed review first for curative-title heir/descendant discovery; probate is one source and tax delinquency is an overlay
- Outreach rule: drafts stay pending human approval before any send

## Trigger Setup

- Set `TRIGGER_PROJECT_REF` in `.env` before running Trigger commands.
