# Diff Summary — SMS Vapi-Style Contextual LLM Replies

## Scope

Adds a safer, less robotic SMS reply path modeled after the existing Vapi integration pattern: Ares owns policy/state/context; provider transport remains isolated; an optional LLM can rewrite reply copy only after deterministic gates allow a draft/auto-ack action.

## Files changed

- `.env.example`
  - Adds disabled-by-default SMS LLM env contract.
- `app/core/config.py`
  - Adds `SMS_AGENT_LLM_REPLIES_ENABLED`, provider/model/temperature/timeout settings.
- `app/db/contacts.py`
  - Normalizes phone variants for inbound lookup so TextGrid E.164 values can match stored national-format contacts.
- `app/db/messages.py`
  - Adds recent-message retrieval for SMS context from memory and Supabase backends.
- `app/services/sms_agent_service.py`
  - Enqueues full inbound body and lead context.
  - Builds reply context from persisted message, lead facts, and recent SMS history before decisioning.
- `app/services/sms_reply_agent_service.py`
  - Adds policy-preserving optional LLM copy rewrite.
  - Keeps deterministic policy/actions/safety gates authoritative.
  - Adds sender allowlist check for auto-ack when configured.
  - Rejects unsafe/empty/overlong LLM replies and falls back to deterministic safe copy.
- `docs/runbooks/textgrid-sms-reply-agent-activation.md`
  - Updates auto-reply activation gate and LLM env guidance.
- `docs/runbooks/sms-vapi-style-contextual-reply-agent.md`
  - New architecture/runbook note mapping the Vapi pattern to SMS.
- `tests/...`
  - Adds coverage for LLM humanization/fallback, auto-ack allowlist, phone lookup normalization, recent message context, and runtime config contract.
- `CONTEXT.md`, `TODO.md`, `memory.md`
  - Updates active handoff docs with the SMS contextual reply direction and gates.

## Safety invariants preserved

- LLM cannot change send policy, action, consent, suppression, urgency, allowlist, or provider gates.
- Global defaults remain no-send/draft-only:
  - `PROVIDER_LIVE_SENDS_ENABLED=false`
  - `SMS_AGENT_AUTO_REPLIES_ENABLED=false`
  - `SMS_AGENT_MODE=draft_only`
  - `SMS_AGENT_LLM_REPLIES_ENABLED=false`
- Auto-replies still require explicit live-send gates and sender allowlist for scoped smoke/prod activation.
- No seller outreach, campaign enrollment, provider activation, or production env toggle was performed by this code slice.
