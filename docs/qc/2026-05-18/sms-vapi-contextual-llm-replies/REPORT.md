# REPORT — SMS Vapi-Style Contextual LLM Replies

## Summary

Implemented the next SMS reply-agent slice for Ares: replies can now be context-aware and LLM-humanized without giving the LLM control over safety policy or sends.

This addresses the owned-number smoke finding that the reply loop was technically working but sounded too deterministic/robotic. The durable product fix is not random templates; it is a Vapi-style split:

- deterministic code decides whether a reply is allowed;
- Ares retrieves lead + conversation context;
- optional LLM writes only the final SMS copy;
- Ares validates the copy and falls back if unsafe;
- Slack/Mission Control remain the operator surfaces for handoff.

## What changed

- Added disabled-by-default SMS LLM settings:
  - `SMS_AGENT_LLM_REPLIES_ENABLED=false`
  - `SMS_AGENT_LLM_PROVIDER=openai_compat | anthropic`
  - `SMS_AGENT_LLM_MODEL=gpt-4o-mini`
  - `SMS_AGENT_LLM_TEMPERATURE=0.4`
  - `SMS_AGENT_LLM_TIMEOUT_SECONDS=8.0`
- Added OpenAI-compatible and Anthropic JSON POST support using stdlib `urllib`.
- Added LLM prompt construction with real-estate acquisition guardrails.
- Added LLM output sanitizer:
  - max 280 chars;
  - non-empty;
  - no high-risk legal/tax/payment/guarantee language;
  - falls back to deterministic draft if invalid.
- Added context retrieval before SMS decisions:
  - persisted inbound message body;
  - recent SMS messages;
  - lead facts such as property address/type, timeline, seller goal, booking status, notes, and consent.
- Added phone lookup normalization so TextGrid E.164 inbound numbers can match stored US national-format records.
- Added auto-ack allowlist enforcement when `SMS_AGENT_ALLOWED_FROM_NUMBERS` is configured.
- Updated runbooks and live handoff docs.

## Vapi analogy captured

New runbook: `docs/runbooks/sms-vapi-style-contextual-reply-agent.md`.

The SMS pattern now mirrors Vapi:

- provider transport is isolated;
- Ares owns state and policy;
- provider events normalize into Ares records;
- Slack/operator handoff stays separate from provider dispatch;
- LLM/tooling can assist language, but not approval or policy.

## Owned-number smoke status

- The earlier no-reply symptom was not a broad TextGrid send failure.
- A manual recovery SMS sent through Ares/TextGrid reached final provider status `delivered`.
- The temporary watcher was updated outside the repo to poll recent TextGrid messages unfiltered and filter locally because provider-side From/To filtered listing missed known inbound messages during the smoke.
- The local watcher was restarted with a bounded owned-number scope and Hermes-assisted copy generation for the active smoke only.
- This local watcher remains outside the repo and is not production seller auto-reply activation.

## Verification

Captured in `test-output.txt`:

- Focused SMS/config regression set:
  - `68 passed in 0.41s`
- Full backend suite:
  - `1153 passed in 21.82s`
- Diff check:
  - `git diff --check` passed

## Safety / side-effect report

No production side effects were performed by this code slice:

- No seller SMS/email/call.
- No global SMS auto-reply enablement.
- No Instantly upload or send.
- No Vapi dispatch.
- No HubSpot/provider write.
- No Supabase remote migration.
- No VPS deploy.
- No live Slack post.

Owned-number local smoke side effects remain limited to Martin's approved number and local run artifacts under `/opt/ares/lead-data/email_marketing_herrington_browne_2026-05-18/`.

## Remaining activation gates

Before any production auto-reply behavior:

1. Configure an LLM provider key in runtime env.
2. Keep `SMS_AGENT_LLM_REPLIES_ENABLED=false` until a scoped smoke is approved.
3. Use `SMS_AGENT_ALLOWED_FROM_NUMBERS` for owned-number smoke.
4. Require `PROVIDER_LIVE_SENDS_ENABLED=true`, `SMS_AGENT_AUTO_REPLIES_ENABLED=true`, and `SMS_AGENT_MODE=auto_ack` only for the approved scope.
5. Verify TextGrid final delivery status, not just queued response.
6. Keep stop/wrong-number/legal/angry/urgent/ambiguous/no-consent replies on human handoff.
