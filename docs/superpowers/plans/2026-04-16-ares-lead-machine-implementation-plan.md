---
title: "Ares Lead Machine Implementation Plan"
status: active
updated_at: "2026-04-16T17:34:10Z"
source_notes:
  - "Ares Lead Machine Superfile 2026"
  - "Hermes — Instantly Lead Automation Final Spec 2026"
  - "2026-04-16 Harris County Probate Keep-Now Ingestion Implementation Plan"
  - "2026-04-16 Curative Title Cold Email Machine Implementation Plan"
---

# Ares Lead Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade lead machine that uses Ares as the source of truth, Instantly as cold outbound transport, Trigger.dev as orchestration, and Mission Control as the operator cockpit. The machine must handle Harris County probate keep-now intake, HCAD enrichment, outbound campaign lifecycle, webhook replay safety, suppression, task generation, and delivery/health surfaces as a single coherent system.

**Architecture:** Keep the machine explicitly event-driven and replay-safe. Model leads, campaigns, memberships, webhook receipts, automation runs, suppression, and tasks as first-class Ares resources. Use Instantly only for transport and provider-side sequencing; never let Instantly become the source of truth. Build the core in memory / fixture-backed first, keep live Supabase wiring out of scope for this slice, and expose the resulting state through Mission Control read models plus a small internal API surface. Separate this cold email machine from the existing lease-option marketing lane; they may share generic primitives, but they do not share domain state.

**Tech Stack:** FastAPI, Pydantic, pytest, the existing in-memory control-plane store, existing audit/usage/secrets/RBAC services, Trigger.dev HTTP jobs, provider retry/preflight helpers, Instantly API v2, and Mission Control read models.

---

## What already exists and must be reused

Do not pretend this is a greenfield repo. The following already exist and are the right foundations:

- The lease-option marketing lane is already implemented in:
  - `app/api/marketing.py`
  - `app/services/marketing_lead_service.py`
  - `app/services/booking_service.py`
  - `app/services/inbound_sms_service.py`
  - `app/models/marketing_leads.py`
  - `app/db/contacts.py`
  - `app/db/tasks.py`
- The generic control-plane pieces already exist and should be reused:
  - `app/db/client.py`
  - `app/db/__init__.py`
  - `app/services/audit_service.py`
  - `app/services/usage_service.py`
  - `app/services/secrets_service.py`
  - `app/services/rbac_service.py`
  - `app/services/permission_service.py`
  - `app/services/provider_retry_service.py`
  - `app/services/provider_preflight_service.py`
  - `app/services/mission_control_service.py`
  - `app/api/mission_control.py`
  - `app/main.py`
- The current phase-3 control-plane slice already proved the repo can carry a larger event model with audit, secrets, usage, and Mission Control projections.
- The existing provider helper style is simple and transport-focused:
  - `app/providers/resend.py`
  - `app/providers/textgrid.py`
  - `app/providers/calcom.py`
- The repo already has a clean in-memory + deferred-Supabase control-plane split. Keep using that pattern. Do not add live Supabase wiring for the lead machine in this slice.

---

## Instantly API surface map to account for up front

This is the important part. The implementation plan should explicitly model the API surface instead of discovering it piecemeal later.

### Core docs and rules

- Authorization uses a Bearer token header.
  - Doc: Authorization
  - Header form: `Authorization: Bearer token`
- Rate limiting is workspace-wide and shared across v1/v2.
  - Doc: Rate Limit
  - Limits: 100 requests/second, 6,000 requests/minute
  - Operational guidance from the docs: batch calls, spread jobs 2–4 times/day, and wait between batches.
- Webhook events are a first-class integration surface, not an afterthought.
  - Doc: Webhook events
  - The payload has base fields and optional email/reply/step metadata.

### Campaign resources and actions to model

The docs expose a full campaign lifecycle, not just “create and hope.” The plan should account for:

- Create campaign
- List campaign
- Get campaign
- Patch campaign
- Delete campaign
- Activate/start/resume campaign
- Stop/pause campaign
- Search campaigns by lead email
- Share campaign
- Create campaign from shared one
- Export campaign to JSON
- Duplicate campaign
- Get launched campaigns count
- Add campaign variables
- Get campaign sending status

The create-campaign endpoint already shows the kind of knobs we need to preserve in our internal campaign model:

- `campaign_schedule`
- `pl_value`
- `is_evergreen`
- `sequences`
- `email_gap`
- `random_wait_max`
- `text_only`
- `first_email_text_only`
- `email_list`
- `daily_limit`
- `stop_on_reply`
- `email_tag_list`
- `link_tracking`
- `open_tracking`
- `stop_on_auto_reply`
- `daily_max_leads`
- `prioritize_new_leads`
- `auto_variant_select`
- `match_lead_esp`
- `stop_for_company`
- `insert_unsubscribe_header`
- `allow_risky_contacts`
- `disable_bounce_protect`
- `limit_emails_per_company_override`
- `cc_list`
- `bcc_list`
- `owned_by`
- `ai_sdr_id`
- `provider_routing_rules`

That is not a toy object. Our internal model needs to preserve these fields cleanly.

### Lead resources and actions to model

The lead API is also richer than a basic contact record. The plan must account for:

- Create lead
- List leads
- Get lead
- Patch lead
- Delete lead
- Delete leads in bulk
- Add leads in bulk to a campaign or list
- Merge two leads
- Move leads to a campaign or list
- Bulk assign leads to organization users
- Update the interest status of a lead
- Remove a lead from a subsequence
- Move a lead to a subsequence

The docs show two important lead-entry paths:

1. Single-create path: `POST /api/v2/leads`
2. Bulk-add path: `POST /api/v2/leads/add`

The bulk add endpoint is especially important because it makes clear that the machine needs to support real production import semantics:

- up to 1000 leads per request
- `campaign_id` OR `list_id`, not both
- `skip_if_in_workspace`
- `skip_if_in_campaign`
- `skip_if_in_list`
- `blocklist_id`
- `assigned_to`
- `verify_leads_on_import`
- lead validation, duplicate skipping, blocklist skipping, and summary counts

The single-create endpoint exposes the richer lead object shape we should preserve internally:

- `campaign`
- `email`
- `personalization`
- `website`
- `last_name`
- `first_name`
- `company_name`
- `job_title`
- `phone`
- `lt_interest_status`
- `pl_value_lead`
- `list_id`
- `assigned_to`
- `skip_if_in_workspace`
- `skip_if_in_campaign`
- `skip_if_in_list`
- `blocklist_id`
- `verify_leads_for_lead_finder`
- `verify_leads_on_import`
- `custom_variables`

The response shape also matters because it carries state we need for projections and reconciliation:

- counts for opens/replies/clicks
- `company_domain`
- `status_summary`
- `status_summary_subseq`
- `last_step_*`
- `email_opened_*`, `email_replied_*`, `email_clicked_*`
- `verification_status`
- `enrichment_status`
- `upload_method`
- `is_website_visitor`
- `esp_code`
- `esg_code`
- timestamps for last contact/open/reply/click/interest change/touch

### Account-campaign mapping

This is a useful dedupe and routing primitive:

- `GET /api/v2/account-campaign-mappings/{email}`
- Scope: `account_campaign_mappings:read` or equivalent all-scope variants
- Use case: determine which campaigns already touch a mailbox / email before routing a lead again

### Webhook resources and event taxonomy

The webhook resource itself has CRUD plus operational controls:

- List webhooks
- Create webhook
- Get webhook
- Patch webhook
- Delete webhook
- List available event types
- Test a webhook
- Resume a webhook

The event taxonomy from the webhook guide must be modeled explicitly. Core event groups include:

- Email events:
  - `email_sent`
  - `email_opened`
  - `reply_received`
  - `auto_reply_received`
  - `link_clicked`
  - `email_bounced`
  - `lead_unsubscribed`
  - `account_error`
  - `campaign_completed`
- Lead status events:
  - `lead_neutral`
  - `lead_interested`
  - `lead_not_interested`
- Meeting events:
  - `lead_meeting_booked`
  - `lead_meeting_completed`
- Other lead events:
  - `lead_closed`
  - `lead_out_of_office`
  - `lead_wrong_person`
- Custom labels:
  - custom workspace labels may appear directly as `event_type`

The payload also includes:

- `timestamp`
- `event_type`
- `workspace`
- `campaign_id`
- `campaign_name`
- optional `lead_email`
- optional `email_account`
- optional `unibox_url`
- optional `step`
- optional `variant`
- optional `is_first`
- optional `email_id`
- optional `email_subject`
- optional `email_text`
- optional `email_html`
- optional reply fields
- optional additional lead fields merged from the database

### Nice-to-add Instantly surfaces that should be designed now

Even if they are not in the first core pass, the architecture should already make room for them:

- Email verification
- Lead labels
- Custom tags
- Custom tag mapping
- Block list entries
- Inbox placement test
- Inbox placement analytics
- Inbox placement blacklist & SpamAssassin reports
- Audit log
- CRM actions
- Workspace, workspace member, and workspace group member resources
- SuperSearch enrichment
- DFY email account order
- Background jobs
- Workspace billing

You do not need to implement every one of those immediately, but you do need the model boundaries and transport layer to leave room for them without a redesign.

---

## Build order at a glance

1. Freeze the canonical domain and file map.
2. Add the shared lead/campaign/event/store models.
3. Build the Instantly client + request/retry helpers.
4. Implement campaign/lead import, dedupe, and routing.
5. Implement webhook ingest, replay protection, and suppression.
6. Implement manual task generation and follow-up state transitions.
7. Wire Harris County probate intake and HCAD enrichment into the same machine.
8. Add Mission Control read surfaces and redaction.
9. Add deliverability / verification / blocklist / CRM extras.
10. Wire routers into `app/main.py`, run focused tests, then run the full suite.

---

## Task 1: Freeze the canonical contract and live doc map

**Files:**
- Modify: `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
- Modify: `TODO.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `README.md` only if the repository-level entrypoint mentions the old split in a way that will confuse the next worker

**Goal:** Make the superfile, TODO, and handoff docs point to one lead-machine source of truth and explicitly separate the new cold email machine from the existing lease-option lane.

- [ ] Add the Instantly API compatibility map to the superfile so the architecture captures the full provider surface, not just the happy-path send loop.
- [ ] Explicitly mark the following as separate lanes in the superfile and handoff docs:
  - lease-option / personal-home workflow
  - Harris probate keep-now ingestion
  - cold email machine
- [ ] Mark the older plan docs as source notes, not active TODOs.
- [ ] Add the implementation plan path to the live pointers so the next worker knows where the execution doc lives.
- [ ] Make sure the docs say “do not add live Supabase wiring in this slice” so nobody gets cute.

**Verification:**
- Read back the updated docs and ensure the contract says one thing everywhere.
- Confirm the lead machine is framed as a production system with state, replay safety, and operator projections — not a throwaway workflow.

---

## Task 2: Add the canonical lead-machine domain models

**Files:**
- Create: `app/models/leads.py`
- Create: `app/models/lead_events.py`
- Create: `app/models/campaigns.py`
- Create: `app/models/automation_runs.py`
- Create: `app/models/suppression.py`
- Modify: `app/models/tasks.py`
- Modify: `app/models/mission_control.py` if the read-model summaries need to expose new lead-machine state

**Goal:** Define the internal source-of-truth shapes for leads, events, campaigns, runs, suppression, and tasks so every later service works from the same vocabulary.

- [ ] Define a canonical `LeadRecord` that can represent both probate-originated leads and Instantly-synced outbound leads.
- [ ] Preserve the Instantly field set directly in the model so we do not lose state in translation:
  - campaign/list membership fields
  - lead identity fields
  - scoring and interest fields
  - verification/enrichment fields
  - counting/timestamp fields
  - payload/custom variable blob
- [ ] Define a `LeadEventRecord` with both internal and provider-facing identifiers so replay protection does not depend on brittle string matching.
- [ ] Define a `CampaignRecord` that keeps schedule, sequencing, warmup, daily limit, stop/suppression flags, sender lists, and routing rules.
- [ ] Define an `AutomationRunRecord` that records the exact workflow execution path and idempotency key.
- [ ] Define a `SuppressionRecord` that records reason, source, campaign scope, and active/archived state.
- [ ] Expand `TaskRecord` and `TaskStatus` so task generation can support more than the current minimal manual-call use case.
- [ ] Keep the existing lease-option task behavior compatible; extend it, do not break it.

**Tests:**
- Create: `tests/models/test_leads.py`
- Create: `tests/models/test_campaigns.py`
- Create: `tests/models/test_automation_runs.py`
- Create: `tests/models/test_suppression.py`
- Modify: `tests/db/test_marketing_repositories.py` only if the expanded task model changes existing task assertions

**Verification commands:**

```bash
pytest tests/models/test_leads.py tests/models/test_campaigns.py tests/models/test_automation_runs.py tests/models/test_suppression.py -q
pytest tests/db/test_marketing_repositories.py -q
```

---

## Task 3: Expand the in-memory store and repository layer

**Files:**
- Modify: `app/db/client.py`
- Modify: `app/db/__init__.py`
- Create: `app/db/leads.py`
- Create: `app/db/lead_events.py`
- Create: `app/db/campaigns.py`
- Create: `app/db/automation_runs.py`
- Create: `app/db/campaign_memberships.py`
- Create: `app/db/suppression.py`
- Create: `app/db/provider_webhooks.py`
- Modify: `app/db/tasks.py`

**Goal:** Give the lead machine a local, replay-safe repository layer before anyone thinks about real persistence or provider wiring.

- [ ] Add store slots for every lead-machine resource, including raw provider receipts and dedupe indexes.
- [ ] Add reset logic for every new store slot.
- [ ] Keep the repository layer in-memory first and defer any live Supabase behavior.
- [ ] Add repositories that can:
  - upsert leads
  - append lead events
  - upsert campaigns
  - record campaign memberships
  - create automation runs
  - update suppression state
  - persist webhook receipts and idempotency keys
- [ ] Make the repository keys explicit and deterministic so replay safety can be tested.
- [ ] Ensure the repository API is symmetric with the existing repo style used for contacts, tasks, runs, approvals, and audit.
- [ ] Add a task repository path that can store `lead_id`, `automation_run_id`, `source_event_id`, `task_type`, `priority`, `due_at`, `assigned_to`, and `idempotency_key`.

**Tests:**
- Create: `tests/db/test_leads_repository.py`
- Create: `tests/db/test_lead_events_repository.py`
- Create: `tests/db/test_campaigns_repository.py`
- Create: `tests/db/test_automation_runs_repository.py`
- Create: `tests/db/test_campaign_memberships_repository.py`
- Create: `tests/db/test_suppression_repository.py`
- Modify: `tests/db/test_tasks_repository.py`

**Verification commands:**

```bash
pytest tests/db/test_leads_repository.py tests/db/test_lead_events_repository.py tests/db/test_campaigns_repository.py tests/db/test_automation_runs_repository.py tests/db/test_campaign_memberships_repository.py tests/db/test_suppression_repository.py tests/db/test_tasks_repository.py -q
```

---

## Task 4: Build the Instantly transport client and compatibility helpers

**Files:**
- Create: `app/providers/instantly.py`
- Modify: `app/services/provider_retry_service.py` only if a lead-machine-specific retry policy needs one extra knob
- Modify: `app/services/provider_preflight_service.py` only if request shape validation needs provider-specific limits
- Create: `tests/providers/test_instantly.py`
- Create: `tests/services/test_instantly_client_rate_limit.py`

**Goal:** Make Instantly a clean, bounded transport adapter with the full API surface modeled as methods, not as ad hoc HTTP calls spread across services.

- [ ] Implement a client that always sends `Authorization: Bearer token` and never leaks the token in logs or model dumps.
- [ ] Centralize request/response handling so 429/5xx behavior is handled through the existing retry service rather than every caller reinventing it.
- [ ] Expose client methods for the whole core surface:
  - campaign CRUD and lifecycle
  - lead CRUD and bulk ops
  - account-campaign mapping lookup
  - webhook CRUD/test/resume/list-event-types
- [ ] Expose client methods for the nice-to-add surface categories as explicit, read-friendly helpers, even if some start as no-op or read-only wrappers.
- [ ] Implement pagination helpers that follow `starting_after` / `next_starting_after` style cursors.
- [ ] Implement bulk add helpers that respect the docs:
  - 1–1000 leads per request
  - campaign OR list, not both
  - skip flags
  - blocklist selection
  - verification on import
- [ ] Add a helper that can query `account-campaign-mappings/{email}` to support dedupe and routing.
- [ ] Add a helper that can parse webhook event type metadata and normalize the provider payload before it reaches domain services.
- [ ] Make the client rate-limit aware:
  - batch imports in chunks of 100 where appropriate
  - wait between batches
  - fail fast on repeated 429s rather than spinning like a raccoon in a trash fire
- [ ] Keep provider transport and domain policy separate: the client should not decide business routing.

**Verification commands:**

```bash
pytest tests/providers/test_instantly.py tests/services/test_instantly_client_rate_limit.py -q
```

---

## Task 5: Build campaign catalog, lead intake, scoring, and routing

**Files:**
- Create: `app/services/campaign_catalog_service.py`
- Create: `app/services/lead_intake_service.py`
- Create: `app/services/lead_scoring_service.py`
- Create: `app/services/lead_routing_service.py`
- Create: `app/services/lead_machine_service.py`
- Create: `app/api/lead_machine.py`
- Modify: `app/services/mission_control_service.py` only if the new machine needs a projection helper for current state

**Goal:** Turn raw inputs into canonical leads, score them deterministically, and route them to the right outbound path without mutating provider state prematurely.

- [ ] Define the lead intake contract for probate-originated leads and outbound-synced leads.
- [ ] Normalize incoming data into the canonical lead model before any outbound action is taken.
- [ ] Implement a deterministic scoring function with explicit inputs and stable output:
  - source quality
  - probate category / filing type
  - HCAD match confidence
  - mailing address availability
  - dedupe certainty
  - suppression state
  - previous campaign exposure
- [ ] Implement routing rules that choose:
  - cold outbound campaign
  - nurture / non-cold path
  - suppress only
  - exception / manual review
- [ ] Add campaign selection logic that can use current capacity, owner assignment, and account-campaign mapping.
- [ ] Make the router consult suppression before queueing any provider action.
- [ ] Emit `lead.created`, `lead.scored`, `lead.routed`, and `automation_run` updates from this layer.
- [ ] Keep route decisions idempotent using a deterministic key derived from tenant + lead + campaign + phase.
- [ ] Keep the `marketing` lease-option lane untouched unless a generic helper is genuinely reusable.

**Tests:**
- Create: `tests/services/test_lead_intake_service.py`
- Create: `tests/services/test_lead_scoring_service.py`
- Create: `tests/services/test_lead_routing_service.py`
- Create: `tests/api/test_lead_machine.py`

**Verification commands:**

```bash
pytest tests/services/test_lead_intake_service.py tests/services/test_lead_scoring_service.py tests/services/test_lead_routing_service.py tests/api/test_lead_machine.py -q
```

---

## Task 6: Build outbound enrollment, sequence progression, and manual task generation

**Files:**
- Create: `app/services/lead_outbound_service.py`
- Create: `app/services/lead_sequence_runner.py`
- Create: `app/services/lead_task_service.py`
- Modify: `app/models/tasks.py`
- Modify: `app/db/tasks.py`
- Modify: `app/services/usage_service.py` only if outbound usage events need a new event kind

**Goal:** Make the cold email machine actually behave like a machine: enqueue leads, progress sequences, and create exactly one operator task for exactly one confirmed send.

- [ ] Build the outbound enqueue path so the service can add one lead or a batch of leads to a campaign/list.
- [ ] Preserve Instantly skip semantics exactly:
  - skip if already in workspace
  - skip if already in campaign
  - skip if already in list
  - honor blocklists
  - optionally verify on import
- [ ] Implement the sequence runner as a real state machine with explicit next-step transitions.
- [ ] Make the task generator fire only on confirmed `email.sent` events.
- [ ] Enforce the hard rule that queued/requested/attempted/failed sends do not create manual call tasks.
- [ ] Make sure one send event creates at most one task.
- [ ] Persist enough state to prevent duplicate tasks after webhook replay, worker retries, or campaign re-imports.
- [ ] Emit task lifecycle events and usage/audit events for every write path that matters.
- [ ] Keep suppression checks ahead of any next-step send.

**Tests:**
- Create: `tests/services/test_lead_outbound_service.py`
- Create: `tests/services/test_lead_sequence_runner.py`
- Create: `tests/services/test_lead_task_service.py`

**Verification commands:**

```bash
pytest tests/services/test_lead_outbound_service.py tests/services/test_lead_sequence_runner.py tests/services/test_lead_task_service.py -q
```

---

## Task 7: Build webhook ingest, event normalization, and suppression state transitions

**Files:**
- Create: `app/services/lead_webhook_service.py`
- Create: `app/api/lead_webhooks.py`
- Create: `app/services/lead_suppression_service.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py` if a new read surface is needed for lead-machine events

**Goal:** Ingest Instantly webhooks safely, normalize them into Ares events, and drive suppression and follow-up transitions without double-counting anything.

- [ ] Verify webhook deliveries if the provider supports a signing mechanism or shared secret; otherwise gate the endpoint with the repo’s own auth and record the trust model explicitly.
- [ ] Normalize every webhook payload into a canonical `LeadEventRecord`.
- [ ] Persist the raw provider receipt separately from the normalized event so we can debug without exposing it in the cockpit.
- [ ] Implement idempotency using a stable key derived from provider event ID, campaign ID, lead email, and email ID when present.
- [ ] Map provider events to internal event types:
  - `email_sent`
  - `email_opened`
  - `reply_received`
  - `auto_reply_received`
  - `link_clicked`
  - `email_bounced`
  - `lead_unsubscribed`
  - `account_error`
  - `campaign_completed`
  - lead status and meeting events
  - other lead events
- [ ] On reply, bounce, unsubscribe, or do-not-contact equivalents, update suppression before any further send path can fire.
- [ ] On `campaign_completed`, close out the run or mark the campaign as exhausted depending on our internal state.
- [ ] On `lead_interested` / `lead_neutral` / `lead_not_interested`, update lead status and route to the proper next step.
- [ ] On `email_opened` / `link_clicked`, update analytics counters but do not create tasks.
- [ ] On `email_sent`, create exactly one manual call task.
- [ ] Keep replay safety explicit: if the exact same webhook lands twice, the second one is a no-op.

**Tests:**
- Create: `tests/services/test_lead_webhook_service.py`
- Create: `tests/services/test_lead_suppression_service.py`
- Create: `tests/api/test_lead_webhooks.py`

**Verification commands:**

```bash
pytest tests/services/test_lead_webhook_service.py tests/services/test_lead_suppression_service.py tests/api/test_lead_webhooks.py -q
```

---

## Task 8: Wire Harris County probate keep-now intake and HCAD enrichment into the same machine

**Files:**
- Create: `app/services/harris_probate_ingest_service.py`
- Create: `app/services/hcad_enrichment_service.py`
- Create: `app/services/probate_to_lead_machine_service.py`
- Create: `app/api/probate.py` or extend `app/api/lead_machine.py` if that keeps the surface smaller
- Modify: `app/services/mission_control_service.py` only if new probate queue projections are needed

**Goal:** Make the primary lead source feed the same canonical machine instead of inventing a second parallel workflow.

- [ ] Preserve the keep-now filter exactly as defined in the superfile.
- [ ] Save raw probate rows for traceability before normalization.
- [ ] Normalize probate filings into canonical leads.
- [ ] Run HCAD matching as an enrichment step, not as a source of truth.
- [ ] Score the lead deterministically and attach the score to the canonical record.
- [ ] Route eligible probate leads into the outbound machine only after suppression and dedupe checks.
- [ ] Surface unmatched or noisy filings as exceptions, not as silent drops.
- [ ] Keep this lane first-class in Mission Control because it is the primary emphasis of the whole machine.

**Tests:**
- Create: `tests/services/test_harris_probate_ingest_service.py`
- Create: `tests/services/test_hcad_enrichment_service.py`
- Create: `tests/api/test_probate.py`

**Verification commands:**

```bash
pytest tests/services/test_harris_probate_ingest_service.py tests/services/test_hcad_enrichment_service.py tests/api/test_probate.py -q
```

---

## Task 9: Add Mission Control read surfaces and redact sensitive data

**Files:**
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `app/main.py` if a new router is introduced for lead-machine read surfaces

**Goal:** Give operators a cockpit that shows the machine clearly without leaking secrets, tokens, or raw provider payloads back into the UI.

- [ ] Add dashboard projections for the cold email machine:
  - campaign counts
  - active sends
  - reply counts
  - bounce / unsubscribe counts
  - suppression counts
  - webhook lag / replay backlog
  - due tasks
  - exception counts
- [ ] Add inbox / thread projections for lead activity and operator follow-up.
- [ ] Add campaign detail projections that show status, health, and next action.
- [ ] Add a lead timeline projection that can show the canonical event stream in order.
- [ ] Redact plaintext secrets, webhook signatures, provider tokens, and raw provider payloads from every read model.
- [ ] Keep the read model thin and backend-owned; the frontend should not invent state.
- [ ] Preserve the existing Mission Control marketing / lease-option projections while adding the new lead-machine ones.

**Tests:**
- Create: `tests/api/test_mission_control_lead_machine.py`
- Modify: `tests/api/test_mission_control_phase3.py` only if the new projections should be merged into the existing assertions

**Verification commands:**

```bash
pytest tests/api/test_mission_control_lead_machine.py tests/api/test_mission_control_phase3.py -q
```

---

## Task 10: Add the deliverability, verification, blocklist, label, tag, audit, and CRM extras

**Files:**
- Extend: `app/providers/instantly.py`
- Create: `app/services/email_verification_service.py`
- Create: `app/services/deliverability_service.py`
- Create: `app/services/inbox_placement_service.py`
- Create: `app/services/blocklist_service.py`
- Create: `app/services/lead_labels_service.py`
- Create: `app/services/custom_tags_service.py`
- Create: `app/services/crm_actions_service.py`
- Optionally create dedicated API routers:
  - `app/api/email_verification.py`
  - `app/api/deliverability.py`
  - `app/api/blocklists.py`
  - `app/api/lead_labels.py`
  - `app/api/crm_actions.py`

**Goal:** Design the next layer now so we do not have to redesign the machine when deliverability or ops becomes the bottleneck.

- [ ] Model lead labels and custom tags as first-class resources instead of stuffing them into ad hoc metadata blobs.
- [ ] Model blocklists as explicit policy objects that can be checked before any send.
- [ ] Expose email verification and inbox-placement checks as separate read/write flows.
- [ ] Add placeholder-safe support for audit log and CRM action surfaces, even if the first version is read-heavy.
- [ ] Make deliverability health visible in Mission Control and usable by the routing layer.
- [ ] Keep these modules separate from the core send-loop so they can be toggled or replaced later without rewriting the machine.

**Tests:**
- Create: `tests/services/test_email_verification_service.py`
- Create: `tests/services/test_deliverability_service.py`
- Create: `tests/services/test_inbox_placement_service.py`
- Create: `tests/services/test_blocklist_service.py`
- Create: `tests/services/test_lead_labels_service.py`
- Create: `tests/services/test_custom_tags_service.py`
- Create: `tests/services/test_crm_actions_service.py`

**Verification commands:**

```bash
pytest tests/services/test_email_verification_service.py tests/services/test_deliverability_service.py tests/services/test_inbox_placement_service.py tests/services/test_blocklist_service.py tests/services/test_lead_labels_service.py tests/services/test_custom_tags_service.py tests/services/test_crm_actions_service.py -q
```

---

## Task 11: Wire governance, secrets, audit, usage, and permissions around the machine

**Files:**
- Modify: `app/services/secrets_service.py`
- Modify: `app/services/rbac_service.py`
- Modify: `app/services/permission_service.py`
- Modify: `app/services/audit_service.py` only if a new lead-machine event category needs a small adapter
- Modify: `app/services/usage_service.py` only if outbound/provider events need a new usage classification
- Modify: `app/api/rbac.py`
- Modify: `app/api/secrets.py`
- Modify: `app/api/audit.py`
- Modify: `app/api/usage.py`

**Goal:** Make the machine enterprise-safe from the start: secrets are bound resources, write paths are auditable, and operators only see what their role should allow.

- [ ] Store Instantly API keys as secret resources, not loose env notes.
- [ ] Bind provider credentials to the lead machine through first-class secret bindings.
- [ ] Add RBAC permissions for lead-machine read/write/admin operations.
- [ ] Add permissions for provider credentials, deliverability, and webhook administration.
- [ ] Emit audit events from every meaningful write path:
  - campaign create/update/delete
  - lead import/add/move/merge
  - webhook create/resume/delete/test
  - suppression changes
  - task creation and completion
  - credential binding changes
- [ ] Record usage for outbound-provider calls and webhook processing where the existing usage model expects it.
- [ ] Redact secret values in all API responses and Mission Control surfaces.

**Tests:**
- Modify / extend the existing RBAC, secret, audit, and usage tests:
  - `tests/api/test_rbac.py`
  - `tests/api/test_secrets.py`
  - `tests/api/test_audit.py`
  - `tests/api/test_usage.py`
- Add lead-machine-specific auth tests if the new routers need them:
  - `tests/api/test_lead_machine_auth.py`
  - `tests/api/test_lead_webhooks_auth.py`

**Verification commands:**

```bash
pytest tests/api/test_rbac.py tests/api/test_secrets.py tests/api/test_audit.py tests/api/test_usage.py -q
```

---

## Task 12: Wire routers, package exports, smoke tests, and the full-suite gate

**Files:**
- Modify: `app/main.py`
- Modify: `app/db/__init__.py`
- Modify: `tests/test_package_layout.py`
- Modify: `tests/smoke/test_health.py` only if the app boot surface changes
- Update docs only if a new router or command path must be reflected in the handoff

**Goal:** Make the app boot cleanly with the new routers, keep the package layout honest, and validate the entire slice end-to-end.

- [ ] Include the new routers in `app/main.py`.
- [ ] Keep the existing marketing router mounted; do not replace it with the lead machine.
- [ ] Export the new repository modules from `app/db/__init__.py` if package layout tests expect it.
- [ ] Update `tests/test_package_layout.py` so the new modules are recognized.
- [ ] Run the targeted DB/API/service tests first.
- [ ] Run the full Python suite only after the focused tests are green.
- [ ] If a test fails, fix the code, not the test, unless the test is genuinely wrong.

**Verification commands:**

```bash
pytest tests/db/test_leads_repository.py tests/db/test_lead_events_repository.py tests/db/test_campaigns_repository.py tests/db/test_automation_runs_repository.py tests/db/test_campaign_memberships_repository.py tests/db/test_suppression_repository.py tests/db/test_tasks_repository.py -q
pytest tests/providers/test_instantly.py tests/services/test_instantly_client_rate_limit.py tests/services/test_lead_intake_service.py tests/services/test_lead_scoring_service.py tests/services/test_lead_routing_service.py tests/services/test_lead_outbound_service.py tests/services/test_lead_sequence_runner.py tests/services/test_lead_task_service.py tests/services/test_lead_webhook_service.py tests/services/test_lead_suppression_service.py tests/services/test_harris_probate_ingest_service.py tests/services/test_hcad_enrichment_service.py tests/services/test_email_verification_service.py tests/services/test_deliverability_service.py tests/services/test_inbox_placement_service.py tests/services/test_blocklist_service.py tests/services/test_lead_labels_service.py tests/services/test_custom_tags_service.py tests/services/test_crm_actions_service.py -q
pytest tests/api/test_lead_machine.py tests/api/test_lead_webhooks.py tests/api/test_probate.py tests/api/test_mission_control_lead_machine.py tests/api/test_lead_machine_auth.py tests/api/test_lead_webhooks_auth.py -q
pytest -q
```

---

## Lead-machine operating rules that must not move

- Ares is the source of truth.
- Instantly is transport, sequencing, and webhook delivery only.
- Resend is not the cold outbound sequencer.
- The existing lease-option lane stays separate.
- `email.sent` is the only webhook event that can create the manual call task.
- `queued`, `requested`, `attempted`, or `failed` sends do not create the task.
- Any reply, bounce, unsubscribe, or do-not-contact state overrides future sends.
- Duplicate imports, duplicate webhooks, and worker retries must be idempotent.
- Mission Control should explain the machine without lying about backend state.
- No live Supabase wiring in this slice.

---

## Event mapping appendix

Use this map when wiring Instantly webhook events into Ares:

- `email_sent` -> `lead.email.sent`
- `email_opened` -> `lead.email.opened`
- `reply_received` -> `lead.reply.received`
- `auto_reply_received` -> `lead.reply.auto_received`
- `link_clicked` -> `lead.email.clicked`
- `email_bounced` -> `lead.email.bounced`
- `lead_unsubscribed` -> `lead.suppressed.unsubscribe`
- `account_error` -> `provider.account_error`
- `campaign_completed` -> `campaign.completed`
- `lead_neutral` -> `lead.status.neutral`
- `lead_interested` -> `lead.status.interested`
- `lead_not_interested` -> `lead.status.not_interested`
- `lead_meeting_booked` -> `lead.meeting.booked`
- `lead_meeting_completed` -> `lead.meeting.completed`
- `lead_closed` -> `lead.status.closed`
- `lead_out_of_office` -> `lead.status.out_of_office`
- `lead_wrong_person` -> `lead.status.wrong_person`

If a provider-specific custom label arrives as `event_type`, preserve it as a custom event and do not throw it away.

---

## Final gate

The machine is not done until all of these are true:

- A lead can enter through probate intake or a provider import and land in one canonical model.
- The same lead can be deduped against prior campaign exposure.
- The machine can send, receive webhooks, and suppress itself correctly.
- One confirmed send creates one manual task and only one.
- Replay of the same webhook does not create duplicate events or duplicate tasks.
- Mission Control shows the machine without leaking secrets.
- The test suite passes end-to-end.
- The repo still boots cleanly.

