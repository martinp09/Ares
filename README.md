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

## Current Operating-Spine Status

- HubSpot operating spine / agentic company Phases 1-9 are complete and pushed on commit `8c19c26`, with Ares remaining canonical and providers behind preview/apply gates.
- HubSpot portal customization itself has also been live-applied after operator instruction: Ares property groups/properties are present, and Ares stages were added to the existing single HubSpot `Sales Pipeline`.
- First HubSpot record-sync canary is complete: one synthetic contact/deal pair was created and provider-linked after the remote provider-links migration was applied; no batch sync.
- First real HubSpot lead sync is complete: one hand-selected Harris probate lead (`lead_341`, case `543678`) created HubSpot contact `485815102172` and deal `325123310274`; follow-up corrections added HubSpot properties for probate/heir/contact/mailing/property/tax-overlay metadata, updated those same records with applicant/heir data, and filled standard contact address fields for normal HubSpot visibility; no Instantly/Reacher/Vapi/batch/deploy side effects.
- QC index: `docs/qc/2026-05-14/README.md`
- Final readiness artifacts: `docs/qc/2026-05-14/operating-spine-final-readiness/`
- HubSpot live buildout evidence: `docs/qc/2026-05-14/hubspot-live-buildout/`
- HubSpot record-sync canary evidence: `docs/qc/2026-05-14/hubspot-record-sync-canary/`
- HubSpot real-lead sync evidence: `docs/qc/2026-05-14/hubspot-real-lead-sync/`
- HubSpot rich probate/heir fields evidence: `docs/qc/2026-05-14/hubspot-rich-probate-fields/`
- HubSpot contact visibility correction evidence: `docs/qc/2026-05-14/hubspot-contact-visibility-correction/`
- Operating cadence runbook: `docs/runbooks/agentic-company-operating-cadence.md`
- Provider sync/recovery runbook: `docs/runbooks/provider-sync-and-recovery.md`
- Harris + Montgomery probate autopilot is now operational as a no-send system: Trigger schedules default to live public source + public case-detail party/event/document/contact-candidate enrichment + public CAD/tax/land-record enrichment, Ares keeps no-send approval/suppression gates, case-detail live fetches are restricted to approved public county detail URLs, and Instantly/SMS/Vapi/paid skiptrace remain blocked. Latest QC: `docs/qc/2026-05-15/probate-case-detail-enrichment/`. Before any production no-send rollout, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.

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
- Lease-options landing-page contact intake is owned by Ares through `POST /marketing/leads`; the endpoint preserves seller-fit fields, consent metadata, and attribution from the public form, returns booking/side-effect status, and keeps seller-facing SMS/email plus Trigger reminder side effects gated by `PROVIDER_LIVE_SENDS_ENABLED`. Route Slack operator notifications are independent from prospect-facing send gates and are gated by `SLACK_NOTIFICATIONS_ENABLED`.
- Activation readiness handoff: `docs/activation-readiness-handoff.md`; non-secret gate report: `python scripts/activation_readiness.py --json`. When reusing the existing local VPS env without copying secrets, run `python scripts/activation_readiness.py --json --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults`.

### Slack operator notifications

Slack notifications are disabled by default and independent from prospect-facing send gates. Set `SLACK_NOTIFICATIONS_ENABLED=true`, invite the Ares Slack bot to each target channel, and configure `SLACK_CHANNEL_LEAD_RUNS`, `SLACK_CHANNEL_HOT_LEADS`, `SLACK_CHANNEL_CHIEF_OF_STAFF`, `SLACK_CHANNEL_INSTANTLY_REPLIES`, `SLACK_CHANNEL_LEASE_OPTION_INBOUND`, and `SLACK_CHANNEL_SMS_CALLS`.

Run the no-post readiness check before any live Slack smoke:

```bash
uv run python scripts/slack_notification_readiness.py --json
uv run python scripts/slack_notification_readiness.py --json --render-sample --route hot_leads
uv run python scripts/slack_notification_readiness.py --json --render-sample --route chief_of_staff_digest
```

### Ares Chief of Staff v1

The Chief of Staff digest is a read-only lead desk employee report for Martin. It reads current Ares lead records, buckets them into hot/contact-ready/research/skiptrace/blocked queues, checks existing lead-machine health/morning-brief state without triggering new source pulls, writes human-readable artifacts, and can post a Slack-first worklog to route `chief_of_staff_digest`. The Slack report is written like an employee check-in: what I did, what I recommend next, what is blocked, and what needs Martin's approval. Slack payloads use anonymized lead refs; exact lead names/contact/property details stay in local operator artifacts. It does not send seller outreach, spend paid skiptrace credits, enroll Instantly campaigns, write HubSpot/provider records, call Vapi/SMS/email, run live county/source pulls, or deliver scheduled output to Telegram.

Dry-run without artifacts or Slack:

```bash
uv run python scripts/ares_chief_of_staff_digest.py \
  --business-id limitless \
  --environment prod \
  --limit 5 \
  --dry-run \
  --json
```

Write local artifacts under an explicit root:

```bash
uv run python scripts/ares_chief_of_staff_digest.py \
  --business-id limitless \
  --environment prod \
  --artifact-root /var/lib/ares/lead-machine/artifacts \
  --json
```

Slack delivery is opt-in per run and still skips safely unless `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and `SLACK_CHANNEL_CHIEF_OF_STAFF` are configured:

```bash
uv run python scripts/ares_chief_of_staff_digest.py \
  --business-id limitless \
  --environment prod \
  --send-slack \
  --idempotency-key chief-of-staff:$(date -u +%F)
```

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
- `operator_slack_notification`: Slack `chat.postMessage` operator alert with lead/booking context when `SLACK_NOTIFICATIONS_ENABLED=true`, `SLACK_BOT_TOKEN`, and the route channel are configured; otherwise skipped safely.
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
SLACK_NOTIFICATIONS_ENABLED=false
SLACK_BOT_TOKEN=<set when Slack operator notifications are ready>
SLACK_CHANNEL_LEAD_RUNS=<slack-channel-id>
SLACK_CHANNEL_HOT_LEADS=<slack-channel-id>
SLACK_CHANNEL_CHIEF_OF_STAFF=<optional-chief-of-staff-slack-channel-id>
SLACK_CHANNEL_INSTANTLY_REPLIES=<slack-channel-id>
SLACK_CHANNEL_LEASE_OPTION_INBOUND=<slack-channel-id>
SLACK_CHANNEL_SMS_CALLS=<slack-channel-id>
SLACK_CHANNEL_ERRORS=<optional-slack-channel-id>
TRIGGER_SECRET_KEY=<trigger-secret-key>
TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking
TRIGGER_APPOINTMENT_REMINDER_TASK_ID=marketing-send-appointment-reminder
MARKETING_APPOINTMENT_REMINDERS_ENABLED=true
```

## Communication Agent Scaffold

Ares now has a deterministic provider substrate for broader communications automation, separate from the lease-options landing intake path:

- `POST /sms-agent/messages` sends or dry-runs a generic TextGrid SMS. With `PROVIDER_LIVE_SENDS_ENABLED=false` or `dry_run_only=true`, it returns `dry_run=true` and does not call TextGrid. When live sends are enabled and TextGrid is configured, it requires `contact_id` plus `sms_consent_confirmed=true`, normalizes `to`/`from` to E.164, calls TextGrid, and logs the outbound message.
- `POST /sms-agent/webhooks/textgrid` is a generic TextGrid webhook alias that reuses the existing inbound/status callback processor.
- `POST /sms-agent/internal/process-pending` drains queued reply-agent jobs through the deterministic classifier. Keep `PROVIDER_LIVE_SENDS_ENABLED=false` and `SMS_AGENT_AUTO_REPLIES_ENABLED=false` for the first ingest smoke; only enable deterministic auto-ack after Martin approves an owned-number smoke.
- `scripts/sms_agent_archive_export.py` writes redacted SMS reply-agent Markdown and JSONL archive/eval files under `YYYY/MM/`. It is cold storage only; Supabase remains the live runtime source of truth. The command fails closed unless `--root` or `SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT` is explicitly set.
- `POST /voice/assistants`, `POST /voice/phone-numbers`, and `POST /voice/calls/outbound` scaffold Vapi assistant/number/call payloads. Vapi provider mutations and outbound calls stay dry-run unless both `PROVIDER_LIVE_SENDS_ENABLED=true` and `VAPI_PROVIDER_LIVE_SENDS_ENABLED=true` are set.
- `POST /voice/vapi/webhook` accepts Vapi Server URL messages, including `assistant-request`, `tool-calls`, `status-update`, `transcript`, and `end-of-call-report` shapes. Tool calls are wired into Mission Control context/tools: record search/detail, lane scripts, record updates, opportunity stage movement, task completion, lead qualification, follow-up summaries, and human handoff. The route is protected by the normal Ares runtime bearer auth; when `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true`, it also requires `X-Vapi-Secret: <VAPI_WEBHOOK_SECRET>`. Configure the Vapi Server URL credential/header before live callbacks.

SMS reply-agent archive export:

```bash
SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT="/path/to/redacted/archive" \
  uv run python scripts/sms_agent_archive_export.py --date YYYY-MM-DD --dry-run
```

SMS reply-agent local/hosted ingest smoke:

```bash
uv run python scripts/smoke/textgrid_sms_reply_agent_smoke.py \
  --runtime-url http://localhost:8000 \
  --webhook-secret whsec_123 \
  --from +15551234567 \
  --to +13467725914 \
  --body "Can you call me?"
```

Add `--runtime-api-key <local-runtime-api-key>` only when the runtime gates are intentionally configured for a no-send processor drain. The activation runbook is `docs/runbooks/textgrid-sms-reply-agent-activation.md`.

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
RUNTIME_API_KEY=<local-runtime-api-key>
CONTROL_PLANE_BACKEND=memory
MARKETING_BACKEND=memory
LEAD_MACHINE_BACKEND=memory
SITE_EVENTS_BACKEND=memory
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=<local-runtime-api-key>
VITE_RUNTIME_API_BASE_URL=
```

Startup:

```bash
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
RUNTIME_API_BASE_URL=http://127.0.0.1:8000 RUNTIME_API_KEY=<local-runtime-api-key> npm --prefix apps/mission-control run dev -- --host 127.0.0.1 --port 5173
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000 HERMES_RUNTIME_API_KEY=<local-runtime-api-key> npm --prefix trigger run dev
```

First smoke:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -H 'Authorization: Bearer <local-runtime-api-key>' http://127.0.0.1:8000/hermes/tools
```

## VPS Docker / Tailnet Edge

The VPS deployment is an internal operator surface, not a public unauthenticated API.

Tracked deployment templates:

- `Dockerfile.api` — API image, non-root runtime user, OCI labels.
- `Dockerfile.ui` — Mission Control static image, unprivileged Nginx, port `8080`.
- `deploy/nginx.conf` — SPA fallback plus basic security headers.
- `deploy/Caddyfile.tailnet.example` — Caddy edge template bound to `ARES_TAILNET_IP` and using `ARES_RUNTIME_API_KEY` from systemd environment, never a committed literal.
- `deploy/docker-compose.vps.example.yml` — loopback-only API/UI port publishing plus container hardening knobs.

Live VPS rules:

- Caddy should bind to the tailnet IP only, e.g. `100.74.177.6:80`, with `bind {$ARES_TAILNET_IP}`.
- Caddy may inject the internal runtime bearer only after the tailnet boundary; do not expose this proxy on public `eth0`.
- Keep API/UI Docker ports loopback-only: `127.0.0.1:8000:8000` and `127.0.0.1:8080:8080`.
- Keep Supabase/dev ports blocked from public `eth0`; the current VPS uses `ares-edge-firewall.service` to drop public TCP `80,54321,54322,54323,54324,54327` while allowing tailnet/local access.
- Do not print `/etc/caddy/ares-runtime.env`, raw `Authorization` headers, or runtime bearer values into logs/QC/chat.

## Verification

- Activation gates: `python scripts/activation_readiness.py --json`
  - Existing local VPS env without copying secrets: `python scripts/activation_readiness.py --json --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults`
- Slack operator notification gates: `uv run python scripts/slack_notification_readiness.py --json`
- Provider request shape: `python scripts/smoke_provider_readiness.py`
- Python: `uv run pytest -q`
- Lead machine smoke: `uv run python scripts/smoke/lead_machine_smoke.py`
- Probate autopilot live no-send smoke: `uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD`
- TextGrid SMS reply-agent ingest smoke: `uv run python scripts/smoke/textgrid_sms_reply_agent_smoke.py --runtime-url http://localhost:8000 --webhook-secret <textgrid-webhook-secret> --from <owned-sender> --to <ares-textgrid-number> --body "Can you call me?"`
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
