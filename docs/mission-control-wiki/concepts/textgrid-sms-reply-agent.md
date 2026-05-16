# TextGrid SMS Reply Agent

## Summary

The TextGrid SMS Reply Agent is the Ares reply-handling layer for inbound lead texts to TextGrid numbers. It should receive provider callbacks, resolve the sender to Ares context, classify intent, draft or safely acknowledge, and create Mission Control review work without letting provider callbacks block on slow agent work.

## Operating Model

- TextGrid inbound webhook is the always-on listener.
- Supabase is the operational source of truth for provider receipts, messages, conversations, jobs, decisions, and operator review state.
- Obsidian/JSONL is a redacted cold archive and eval corpus, not the live source of truth.
- Mission Control is the operator surface for approval, edits, suppression, callbacks, and evaluation labels.
- Trigger.dev drains pending reply-agent jobs every minute through a protected Ares internal endpoint.

## Guardrails

- Default mode is `draft_only`.
- STOP and wrong-number replies bypass LLM drafting.
- Auto acknowledgement requires both `PROVIDER_LIVE_SENDS_ENABLED=true` and `SMS_AGENT_AUTO_REPLIES_ENABLED=true`.
- No auto reply can discuss offer terms, legal advice, tax advice, valuation, closing timelines, or promises.
- Ambiguous phone matches create review work and block sends.
- Delivery is not claimed until TextGrid status callback or polling proves final provider state.

## Source Docs

- Spec: `docs/superpowers/specs/2026-05-16-textgrid-sms-reply-agent-design.md`
- Plan: `docs/superpowers/plans/2026-05-16-textgrid-sms-reply-agent-implementation-plan.md`
