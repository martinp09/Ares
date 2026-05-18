# SMS Reply Agent: Vapi-Style Contextual Loop

## Status

Current branch: `feature/ares-chief-of-staff-v0`.

This is an implementation/runbook note for making the SMS agent feel closer to a human employee while preserving Ares safety gates.

## Vapi pattern to mirror

Ares' Vapi integration already separates four responsibilities:

1. **Provider transport** — Vapi owns the voice call transport and call events.
2. **Runtime gates** — Ares only dispatches calls when global provider sends and Vapi-specific live gates are enabled.
3. **Context and metadata** — outbound call payloads include Ares object identity and metadata; webhooks normalize provider events, transcript/summary, handoff markers, and tool results.
4. **Operator reporting** — call events are normalized into Slack-safe notifications and provider-link records without treating the provider as Ares' source of truth.

The SMS agent should use the same shape, with TextGrid as transport:

- TextGrid = transport for inbound/outbound SMS.
- Ares = source of truth for lead/contact/conversation/message/job/decision records.
- SMS reply policy = deterministic safety layer.
- Optional LLM = copywriter for a single allowed reply body only.
- Slack/Mission Control = reporting and manager review surface.

## Non-negotiable policy split

The LLM must never decide whether to send. Ares code decides:

- sender resolved vs ambiguous
- SMS consent present
- suppressed/contact blocked
- stop/wrong-number/legal/angry/urgent handoff
- sender allowlist for auto-reply smoke
- global provider live-send gate
- `SMS_AGENT_AUTO_REPLIES_ENABLED`
- `SMS_AGENT_MODE=auto_ack`

The LLM can only rewrite the already-allowed `suggested_body` into a more natural single SMS. If it returns unsafe/empty/overlong copy, Ares falls back to the deterministic safe draft.

## New v1 SMS context loop

For every inbound SMS job, the processor now builds a `SmsReplyContext` with:

- inbound message body from the persisted message row when available
- lead/contact facts: property address/type, seller goal, timeline, booking status, notes, consent
- recent SMS messages for the contact
- source lane from lead metadata/campaign/source where available
- deterministic intent, urgency, temperature, and action

The reply service then:

1. Classifies the inbound text.
2. Applies safety policy.
3. Builds a deterministic fallback body.
4. If `SMS_AGENT_LLM_REPLIES_ENABLED=true`, calls the configured LLM provider for natural copy.
5. Sanitizes the LLM response.
6. Records whether the LLM was used in decision metadata.

## Activation flags

Default safe posture:

```text
SMS_AGENT_MODE=draft_only
SMS_AGENT_AUTO_REPLIES_ENABLED=false
SMS_AGENT_LLM_REPLIES_ENABLED=false
PROVIDER_LIVE_SENDS_ENABLED=false
```

Owned-number auto-reply smoke only:

```text
PROVIDER_LIVE_SENDS_ENABLED=true
SMS_AGENT_AUTO_REPLIES_ENABLED=true
SMS_AGENT_MODE=auto_ack
SMS_AGENT_ALLOWED_FROM_NUMBERS=<owned-operator-number-only>
SMS_AGENT_LLM_REPLIES_ENABLED=true
SMS_AGENT_LLM_PROVIDER=openai_compat
SMS_AGENT_LLM_MODEL=gpt-4o-mini
SMS_AGENT_LLM_TEMPERATURE=0.4
SMS_AGENT_LLM_TIMEOUT_SECONDS=8.0
```

Provider credentials are optional until the LLM gate is enabled:

```text
OPENAI_COMPAT_API_KEY=<provider-key>
OPENAI_COMPAT_BASE_URL=<optional-openai-compatible-base-url>
# or
ANTHROPIC_API_KEY=<provider-key>
ANTHROPIC_BASE_URL=https://api.anthropic.com
SMS_AGENT_LLM_PROVIDER=anthropic
```

## Human-employee behavior target

Good SMS behavior:

- short, conversational, and specific to the last reply
- one question at a time
- answers identity questions plainly
- moves toward qualification: property/city, authority, motivation, timeline, condition, price/offer preference
- hands off quickly for urgent/legal/angry/wrong-number/stop cases
- never claims legal/tax authority
- never pressures or guarantees an offer
- never invents facts not in Ares context

## Current root-cause note from owned-number smoke

The initial no-reply symptom was not a broad TextGrid send failure. A manual recovery SMS sent through Ares/TextGrid reached final provider status `delivered`. The temporary watcher was updated to poll recent TextGrid messages unfiltered and filter locally because the TextGrid-compatible filtered list query missed known inbound replies during the smoke.

The restored watcher remains local-only and bounded by Martin's owned number, max turns, and expiry. It is not production seller auto-reply activation.
