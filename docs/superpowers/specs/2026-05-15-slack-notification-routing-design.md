# Ares Slack Notification Routing Design

## Status

- Branch: `feature/slack-notification-routing`
- Base: `origin/main` at `247e8a2`
- Scope: design and implementation plan only
- Runtime target: Ares FastAPI runtime, Trigger.dev schedules, Supabase-backed production

## Problem

Ares already has the runtime seams for lead-machine source pulls, no-send enrichment, Instantly webhooks, lease-option website intake, TextGrid inbound SMS, and Vapi call webhooks. Slack is only partially wired: lease-option intake has a one-off Slack side effect behind `PROVIDER_LIVE_SENDS_ENABLED`, and Harris daily import reports Slack readiness without posting.

The requested operator behavior needs a real notification routing layer:

- notify when automatic lead scraping/source pulls run
- notify after enrichment when hot leads need immediate action
- route Instantly replies to a separate channel
- route lease-option website inbound leads to a separate channel
- route SMS replies and incoming calls to a separate channel

## Existing Repo Facts

- `app/core/config.py` already defines `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_LEADS`, `SLACK_CHANNEL_INTAKE`, `SLACK_CHANNEL_HOT_LEADS`, `SLACK_CHANNEL_ERRORS`, and `SLACK_CHANNEL_QC`.
- `app/services/marketing_lead_service.py` contains `_ConfiguredSlackOperatorNotifier`, but it is lease-option specific and coupled to `PROVIDER_LIVE_SENDS_ENABLED`.
- `app/services/harris_daily_lead_machine_service.py` intentionally does not post Slack; it only returns `ready_not_sent` or `skipped_missing_token`.
- `app/services/nightly_lead_machine_service.py` is the current automatic Harris/Montgomery probate autopilot path and produces `MorningBrief` summaries after source pulls, case-detail enrichment, and property/tax/title enrichment.
- `app/services/lead_webhook_service.py` normalizes Instantly provider webhooks into canonical `LeadEventRecord` events and already dedupes provider retries.
- `app/services/inbound_sms_service.py` handles TextGrid inbound SMS/status webhooks, resolves leads, appends inbound messages, and creates review tasks for ambiguous/unmatched replies.
- `app/services/vapi_call_service.py` handles Vapi webhook acceptance and normalizes provider call id/status/transcript/summary.
- Trigger schedules in `trigger/src/lead-machine/probateAutopilotSchedules.ts` run the automatic no-send source/enrichment loop.

## Channel Topology

Use channel IDs in env, not channel names in code.

| Purpose | Suggested Slack channel | Env var | Events |
| --- | --- | --- | --- |
| Automatic lead runs | `#ares-lead-runs` | `SLACK_CHANNEL_LEAD_RUNS` with fallback to `SLACK_CHANNEL_LEADS` | completed/failed source pulls, source health, source counts, warnings |
| Hot leads | `#ares-hot-leads` | `SLACK_CHANNEL_HOT_LEADS` | enriched probate rows with score `>= 70` or explicit `temperature=hot` |
| Instantly replies | `#ares-instantly-replies` | `SLACK_CHANNEL_INSTANTLY_REPLIES` | reply, auto-reply, interested, not-interested, unsubscribe events |
| Lease-option website inbound | `#ares-lease-option-inbound` | `SLACK_CHANNEL_LEASE_OPTION_INBOUND` with fallback to `SLACK_CHANNEL_INTAKE` | accepted `POST /marketing/leads` submissions |
| SMS and calls | `#ares-sms-calls` | `SLACK_CHANNEL_SMS_CALLS` | TextGrid inbound SMS, ambiguous/unmatched SMS, Vapi call lifecycle/summary/handoff events |
| Errors | `#ares-alerts` | `SLACK_CHANNEL_ERRORS` | Slack delivery failures if they need an operator-visible fallback |

Slack channel search from the connected Slack workspace found no existing Ares channels matching these names. The implementation must therefore treat channel creation/channel ID capture as an activation step, not an assumption.

## Design

Create one reusable Slack notification layer:

- `app/models/slack_notifications.py` defines routes, event payloads, and delivery result shapes.
- `app/db/slack_notifications.py` stores delivery attempts and dedupes by `(business_id, environment, route, dedupe_key)`.
- `app/services/slack_notification_service.py` owns channel resolution, message formatting, Slack `chat.postMessage`, failure capture, and safe no-op behavior.
- Producers call the service with normalized business events instead of manually formatting Slack in each API/service.

Slack delivery is an operator notification side effect. It must not be coupled to outbound prospecting gates such as Instantly enrollment, SMS/Vapi dispatch, HubSpot writes, or paid skiptrace. Add a separate gate:

```env
SLACK_NOTIFICATIONS_ENABLED=false
SLACK_BOT_TOKEN=
SLACK_CHANNEL_LEAD_RUNS=
SLACK_CHANNEL_HOT_LEADS=
SLACK_CHANNEL_INSTANTLY_REPLIES=
SLACK_CHANNEL_LEASE_OPTION_INBOUND=
SLACK_CHANNEL_SMS_CALLS=
SLACK_CHANNEL_ERRORS=
```

`PROVIDER_LIVE_SENDS_ENABLED` remains the gate for external prospect-facing sends. Slack notification posting only requires `SLACK_NOTIFICATIONS_ENABLED=true`, a bot token, and the route channel ID.

## Data Flow

### Automatic Source Pulls

Trigger schedule calls `/lead-machine/internal/nightly-source-pull`. `NightlyLeadMachineService.run_nightly_source_pull()` builds and saves a `MorningBrief`, then sends:

- a lead-run digest to `SLACK_CHANNEL_LEAD_RUNS`
- a hot-lead alert to `SLACK_CHANNEL_HOT_LEADS` when enrichment output contains hot records

Hot threshold is `lead_score >= 70`, matching the existing voice-agent hot/warm/cold convention. Warm remains `45 <= score < 70`.

### Instantly Replies

`LeadWebhookService.handle_instantly_webhook()` remains the canonical normalization point. After it appends the canonical `LeadEventRecord`, it sends a Slack notification only for reply/status events that need operator attention:

- `lead.reply.received`
- `lead.reply.auto_received`
- `lead.status.interested`
- `lead.status.not_interested`
- `lead.suppressed.unsubscribe`

Delivery is deduped with the provider receipt/event id so webhook retries do not create duplicate Slack posts.

### Lease-Option Website Inbound

`MarketingLeadService.intake_lead()` continues to upsert the lead and run SMS/email/Trigger side effects. Replace the one-off `_ConfiguredSlackOperatorNotifier` with the shared Slack service route `lease_option_inbound`. This route posts accepted website lead details to `SLACK_CHANNEL_LEASE_OPTION_INBOUND` or `SLACK_CHANNEL_INTAKE`.

The lower-level `/site-events` endpoint remains passive analytics ingestion. It should not post Slack for every event because `POST /marketing/leads` is the lead source of truth.

### SMS Replies And Incoming Calls

`InboundSmsService.handle_textgrid_webhook()` posts only inbound messages, not delivery status callbacks. The Slack message includes resolution state, action (`ignore`, `pause`, `stop`, `qualify`), lead id when resolved, from/to numbers, and body.

`VapiCallService.handle_webhook()` posts accepted call lifecycle events that need operator review, especially call-ended events with summary/transcript/recording metadata and human handoff tool results when available.

## Message Rules

- Include contact information needed for immediate follow-up when Ares has it: name, phone, email, property address, lead id, record id, source lane, lead score, and next action.
- Never include API keys, webhook secrets, bearer tokens, full provider headers, raw auth payloads, or full unfiltered provider payloads.
- Slack blocks should be short and scannable; long raw evidence stays in Ares/Supabase/artifact paths.
- Hot-lead posts cap visible rows at 10 and include counts for hidden rows.
- Every message includes `business_id`, `environment`, route, and dedupe key in context.
- Slack failure must not fail provider webhooks or lead ingestion. It records a failed notification and returns a status object.

## Readiness And Activation

Add `scripts/slack_notification_readiness.py` to validate:

- `SLACK_NOTIFICATIONS_ENABLED`
- `SLACK_BOT_TOKEN`
- route channel IDs
- channel id shape
- optional dry-run message rendering without posting

Activation on the VPS should be:

1. create Slack channels or identify existing private channels
2. invite the Ares Slack bot to each channel
3. set env vars in the deployed runtime/Vercel/Trigger environment
4. run readiness in no-post mode
5. run one approved Slack smoke per route using test payloads

## Acceptance Criteria

- Automatic source pulls send a digest when Slack notifications are enabled and do not send when disabled.
- Hot enriched leads post to the hot-leads channel with enough information to act immediately.
- Instantly replies post to the Instantly replies channel and provider webhook retries do not duplicate posts.
- Lease-option website lead intake posts to the lease-option inbound channel without depending on `PROVIDER_LIVE_SENDS_ENABLED`.
- Inbound SMS replies and Vapi call webhooks post to the SMS/calls channel.
- Slack delivery failures are recorded and surfaced without breaking the source webhook/intake flow.
- Existing no-send/provider-send gates remain intact.
- Tests cover disabled, configured, failed, and deduped Slack paths.
