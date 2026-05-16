# TextGrid SMS Reply Agent Design

Date: 2026-05-16
Branch: `feature/textgrid-sms-agent`
Worktree: `/Users/solomartin/Projects/Ares/.worktrees/feature-textgrid-sms-agent`

## Goal

Build an always-on SMS reply agent for every lead that texts an Ares-owned TextGrid number. The agent must ingest TextGrid callbacks, resolve the sender to Ares lead/contact/deal context, classify the reply, create a safe draft or approved automatic acknowledgement, preserve an evaluation corpus, and keep Supabase as the operational source of truth without turning it into an unbounded transcript warehouse.

## Current repo baseline

Ares already has the right foundation:

- `POST /sms-agent/messages` sends or dry-runs TextGrid SMS through `SmsAgentService`.
- `POST /sms-agent/webhooks/textgrid` reuses `InboundSmsService.handle_textgrid_webhook`.
- `app/providers/textgrid.py` already normalizes Twilio/TextGrid-style payloads and builds outbound TextGrid requests.
- `app/db/messages.py`, `app/db/conversations.py`, and `app/db/provider_webhooks.py` already support Supabase-backed message, thread, and webhook receipt persistence.
- `app/services/voice_agent_service.py` already contains Ares real-estate agent prompting, lane separation, Mission Control tool use, and handoff guardrails that should be reused for SMS.
- Mission Control already exposes replies/inbox concepts with `reply_needs_review`, messages, thread actions, and task completion.
- Production remains no-send by default. `PROVIDER_LIVE_SENDS_ENABLED=false` is the safe baseline, and SMS/Vapi/provider sends are separate explicit approval gates.

This feature should extend the current SMS scaffold. It should not introduce a parallel messaging runtime.

## External provider assumptions

TextGrid publicly positions its SMS API as Twilio-compatible by changing the Twilio base URL to `https://api.textgrid.com`, with outbound/inbound SMS, delivery receipts, opt-out controls, number pooling, and autoresponder support. Because TextGrid's public docs are sparse, the implementation must treat Twilio's webhook contract as the starting contract and verify the actual TextGrid dashboard/request payloads during the first implementation task.

Provider contract to implement against:

- Outbound messages use `POST /2010-04-01/Accounts/{AccountSid}/Messages.json` form fields: `To`, `From`, `Body`, and optional `StatusCallback`.
- Inbound SMS callbacks are form-encoded webhooks containing fields such as `MessageSid` or `SmsSid`, `From`, `To`, and `Body`.
- Delivery callbacks may contain `MessageSid` or `SmsSid` plus `MessageStatus` or `SmsStatus`.
- Signature verification should support both `X-TextGrid-Signature` and `X-Twilio-Signature`, because TextGrid is Twilio-compatible and the existing historical adapter looked for both header names.
- The inbound webhook must acknowledge quickly. It should not wait on an LLM, Supabase-heavy context hydration, or provider send attempts.

Open verification item: confirm in the TextGrid dashboard whether number-level inbound webhooks can send custom headers. If they cannot, the public inbound route must be unauthenticated by Ares bearer auth and protected by TextGrid/Twilio signature validation plus replay/idempotency checks. Do not reintroduce runtime bearer tokens in query strings.

Sources:

- TextGrid SMS API public page: `https://textgrid.com/sms-api/`
- Twilio messaging webhook request guide: `https://www.twilio.com/docs/messaging/guides/webhook-request`

## Product behavior

### Modes

The reply agent has four modes:

1. `record_only`: ingest the reply, update message/thread state, and create review tasks. No LLM call and no outbound send.
2. `draft_only`: generate a suggested reply and show it in Mission Control for operator approval. No outbound send.
3. `auto_ack`: send a narrow, pre-approved acknowledgement only when all live-send gates and policy checks pass.
4. `human_handoff`: create urgent operator work and never auto-send.

Initial rollout should default to `draft_only` for resolved leads and `record_only` for unresolved messages. `auto_ack` stays off until explicitly enabled and verified with owned-number smoke tests.

### Classification

Every inbound reply should be classified into one primary intent:

- `interested`
- `question`
- `appointment_request`
- `not_interested`
- `stop`
- `wrong_number`
- `angry_or_threat`
- `legal_or_tax_sensitive`
- `vendor_or_non_lead`
- `spam`
- `unknown`

Every reply should also carry:

- `source_lane`: `outbound_probate`, `curative_title`, `inbound_lease_option`, `seller_direct`, `buyer_inquiry`, `vendor`, `wrong_number`, or `unknown`.
- `temperature`: `hot`, `warm`, `cold`, or `blocked`.
- `urgency`: `normal`, `high`, or `urgent`.
- `handoff_required`: boolean.
- `suppress_contact`: boolean for STOP, wrong-number, and do-not-contact decisions.
- `next_best_action`: short operator-facing action.

### Safe automatic replies

Automatic replies are only allowed for narrow acknowledgement cases:

- The inbound message resolves to exactly one lead/contact/conversation.
- The lead is not suppressed.
- The contact has SMS consent or the provider/legal stance has been explicitly approved for conversational replies to inbound messages.
- The reply is not STOP, wrong number, angry, legal/tax-sensitive, threatening, attorney/court-related, valuation-related, or price/offer negotiation.
- `PROVIDER_LIVE_SENDS_ENABLED=true`.
- `SMS_AGENT_AUTO_REPLIES_ENABLED=true`.
- The TextGrid number is in `SMS_AGENT_ALLOWED_FROM_NUMBERS`.
- The generated or deterministic reply passes the SMS policy validator.

The first allowed `auto_ack` copy should be deterministic:

- For interested/question replies: "Got it. I am sending this to our property team so a human can review and follow up."
- For appointment requests: "Got it. I will have a human follow up on scheduling."
- For unclear replies: "Thanks. I am going to have a human review this and follow up."

No auto reply may include offer terms, legal advice, valuation claims, closing promises, urgency pressure, or a booking link unless a separate approved campaign policy explicitly permits it.

### STOP and compliance handling

STOP-like replies must bypass the LLM path:

- Mark the sequence/contact suppressed through existing sequence/contact suppression behavior.
- Create a provider webhook receipt and message row.
- Create or update a suppression review task where current data requires review.
- Return quickly to TextGrid.
- Do not send any confirmation from Ares unless TextGrid requires provider-side opt-out response handling.

Wrong-number replies should suppress only after a deterministic match or operator confirmation if the same phone is attached to multiple leads.

## Architecture

### Webhook path

`POST /sms-agent/webhooks/textgrid` should become the public TextGrid number webhook:

1. Parse form-encoded, multipart, or JSON payloads.
2. Verify `X-TextGrid-Signature` or `X-Twilio-Signature` using `TEXTGRID_WEBHOOK_SECRET` or `TEXTGRID_AUTH_TOKEN` according to the confirmed TextGrid dashboard behavior.
3. Normalize the payload with `app.providers.textgrid.normalize_incoming_webhook`.
4. Record a `provider_webhooks` receipt idempotently.
5. Append inbound message and conversation state when the sender resolves.
6. Enqueue an SMS reply-agent job.
7. Return `200` immediately with `<Response></Response>` for inbound callbacks and a simple `200` for status callbacks.

The route should be mounted without the normal Ares runtime bearer dependency. It is a provider callback endpoint, not an operator API endpoint. All internal processing endpoints remain protected by `Authorization: Bearer <RUNTIME_API_KEY>`.

### Processing path

Add a protected internal endpoint:

- `POST /sms-agent/internal/process-pending`

It claims pending jobs, processes them, writes decisions, and optionally sends replies. Trigger.dev runs this endpoint every minute and also supports manual backfill.

Job flow:

1. Claim due jobs with `status='pending'` and `locked_until` empty or expired.
2. Load message, conversation, contact, lead-machine, record, deal, and task context.
3. Run deterministic compliance classification first.
4. If deterministic result is terminal, write decision and perform allowed side effects.
5. If LLM drafting is needed, call the existing runtime provider registry with a small structured prompt.
6. Validate the model output against a strict Pydantic model.
7. Write a reply decision row.
8. If `auto_ack` is allowed, call `SmsAgentService.send_message`.
9. Otherwise create/update Mission Control review work.
10. Mark job `completed`, `blocked`, or `failed_retryable`.

### Data model

Supabase remains the operational source of truth for:

- Provider webhook receipts.
- Current message/conversation rows.
- Reply-agent jobs and decisions.
- Operator review state.
- Short retention evaluation labels.

Supabase should not store unlimited raw LLM prompts, full transcripts, or repeated provider payload copies forever.

Add hot operational tables:

- `sms_agent_jobs`: one row per inbound message requiring processing.
- `sms_agent_decisions`: one row per classification/draft/send decision.
- `sms_agent_eval_labels`: operator/evaluator labels used for regression testing.
- `sms_agent_archives`: pointers to cold archive artifacts and content hashes.

Retention posture:

- `messages.body` remains canonical for current operations and Mission Control.
- `provider_webhooks.payload` keeps the raw provider callback for replay while active.
- `sms_agent_decisions` stores compact structured facts, not full prompts.
- Full prompt/context/transcript bundles are exported to cold artifacts and referenced by hash/path.
- A cleanup job can redact or remove raw provider payloads and old decision context after a configured retention window once archive hashes exist.

### Obsidian/cold archive

Obsidian should be a cold archive and evaluation corpus, not the live system of record.

Recommended local archive root:

`/Users/solomartin/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/Limitless Vault/30-Resources/Ares/SMS Reply Agent`

Archive format:

- Daily Markdown index: `YYYY-MM-DD.md`.
- JSONL corpus next to it: `YYYY-MM-DD.sms-agent-corpus.jsonl`.
- Each entry includes redacted phone/email values, Ares ids, inbound intent, source lane, model decision, final operator action, delivery result, and SHA-256 of the raw bundle.
- Raw PII bundles should stay out of Obsidian unless Martin explicitly approves that storage policy.

Runtime should write archive pointers into Supabase. The local archive writer can run as a protected CLI or scheduled local job that reads decisions from Supabase and writes redacted corpus files into the vault.

### Mission Control

Mission Control should show:

- New `SMS Agent` / `Replies` queue filter.
- Classification badges: intent, temperature, urgency, source lane.
- Suggested reply body with reasons and guardrails.
- Buttons: approve send, edit and send, suppress, wrong number, assign callback, mark resolved.
- Decision audit trail: webhook id, message id, job id, model/provider, prompt version, policy decision, send result.
- Test/eval label control: correct intent, bad draft, unsafe draft, wrong lead, good send, human takeover required.

The first UI slice can reuse the existing inbox detail and `reply_needs_review` surfaces rather than building a separate dashboard.

## Provider and environment configuration

Add envs:

```bash
SMS_AGENT_MODE=draft_only
SMS_AGENT_AUTO_REPLIES_ENABLED=false
SMS_AGENT_ALLOWED_FROM_NUMBERS=+13467725914
SMS_AGENT_PROCESS_BATCH_SIZE=25
SMS_AGENT_MAX_ATTEMPTS=5
SMS_AGENT_LOCK_SECONDS=120
SMS_AGENT_RETENTION_DAYS=90
SMS_AGENT_ARCHIVE_ENABLED=false
SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT="/Users/solomartin/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/Limitless Vault/30-Resources/Ares/SMS Reply Agent"
SMS_AGENT_PROMPT_VERSION=sms_reply_agent_v1
TEXTGRID_INBOUND_WEBHOOK_URL=https://<ares-runtime>/sms-agent/webhooks/textgrid
TEXTGRID_STATUS_CALLBACK_URL=https://<ares-runtime>/sms-agent/webhooks/textgrid
```

Existing envs remain active:

```bash
TEXTGRID_ACCOUNT_SID=<textgrid-account-sid>
TEXTGRID_AUTH_TOKEN=<textgrid-auth-token>
TEXTGRID_FROM_NUMBER=<e164-sender-number>
TEXTGRID_WEBHOOK_SECRET=<textgrid-or-twilio-signing-secret>
PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true
PROVIDER_LIVE_SENDS_ENABLED=false
RUNTIME_API_KEY=<runtime-internal-api-key>
```

## Rollout phases

### Phase 1: Ingest and draft

- Public signed TextGrid inbound webhook.
- Idempotent message/job persistence.
- Deterministic STOP/wrong-number handling.
- LLM or deterministic draft decisions.
- Mission Control review queue.
- No automatic sends.

### Phase 2: Evaluation corpus and archive

- Operator labels on decisions.
- Redacted Obsidian/JSONL export.
- Replay script that runs archived examples through the current prompt/classifier.
- Regression tests for known good/bad replies.

### Phase 3: Controlled auto acknowledgement

- Enable only deterministic acknowledgement copy.
- Allowlist one owned TextGrid number.
- Run one approved live smoke.
- Poll or consume TextGrid status callback before claiming delivery.
- Keep all sales/offer/legal replies in draft-only mode.

### Phase 4: Full reply operations

- Campaign/lane-specific reply policies.
- Per-lead queue throttling.
- Missed-reply SLA alerts.
- Metrics: time to first review, auto-ack rate, unsafe draft rate, wrong-lead rate, conversion from reply to operator task/deal.

## Risks and mitigations

- Provider auth risk: provider callbacks may not support custom headers. Mitigation: public webhook with provider signature verification, no runtime query tokens.
- Supabase bloat risk: raw transcript/context growth. Mitigation: compact decision rows, archive pointers, retention cleanup, redacted Obsidian corpus.
- Unsafe auto-send risk: strict default to draft-only, deterministic terminal compliance rules, separate `SMS_AGENT_AUTO_REPLIES_ENABLED` gate.
- Wrong lead risk: provider-thread match first, tenant-scoped phone match second, ambiguity creates review tasks and blocks sends.
- LLM latency risk: webhook only enqueues, Trigger/internal endpoint processes jobs.
- TextGrid content filtering risk: short tested reply copy, delivery callback verification, no claim of delivery from initial `queued`.

## Success criteria

- TextGrid can hit `/sms-agent/webhooks/textgrid` without Ares bearer auth and receive a fast `200`.
- Duplicate TextGrid callbacks do not duplicate jobs, decisions, messages, tasks, or sends.
- STOP replies never trigger an LLM or outbound reply.
- Ambiguous phone matches create review work and never mutate the wrong lead.
- Resolved replies create a compact decision record and visible Mission Control review item.
- Drafts preserve Ares lane separation between outbound probate/curative-title and inbound lease-option.
- Auto replies are impossible unless every live-send and SMS-agent gate is enabled.
- Redacted archive export can generate a JSONL corpus for prompt/eval testing without making Obsidian the live source of truth.
