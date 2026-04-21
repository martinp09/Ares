---
title: "Probate Outbound + Lease-Option Inbound MVP Implementation Plan"
status: active
updated_at: "2026-04-20T14:12:28Z"
source_notes:
  - "2026-04-16 Ares Real Estate Runtime Thesis"
  - "2026-04-14 Lease-Option Marketing MVP Design"
  - "origin/main 2026-04-16 Ares Lead Machine Implementation Plan"
  - "origin/main 2026-04-16 Harris County Probate Keep-Now Ingestion Plan"
  - "origin/main 2026-04-16 Curative Title Cold Email Machine Plan"
---

# Probate Outbound + Lease-Option Inbound MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship one real two-lane MVP in Ares:

- outbound probate -> cold email -> reply/suppression/task loop
- inbound lease-option -> submit/book/reply/task loop

Both lanes must run through Ares as the deterministic runtime, keep Hermes as the browser/research driver, and keep live Supabase backend wiring delayed until a later pass. This blueprint covers everything else: domain logic, repository contracts, webhook semantics, Mission Control, and tests.

**Architecture:** Keep the lanes separate in domain state and operator surfaces. Reuse the existing lease-option marketing slice already in this branch. Bring the newer probate / lead-machine slice forward from `origin/main` instead of rebuilding it. Share only the runtime primitives that should truly be shared: tenant resolution, provider webhook receipts, tasks, Mission Control read models, and a minimal downstream opportunity skeleton. Keep the storage boundary explicit so memory / fixture-backed execution remains the default in this pass and live Supabase persistence can be switched on later without rewriting the domain layer.

**Tech Stack:** FastAPI, Pydantic, pytest, Trigger.dev, existing Mission Control app, existing lease-option provider adapters, Instantly API v2, and Hermes as the upstream browser-capable driver. Supabase schema / REST wiring is intentionally deferred to a later pass.

---

## Target MVP Shape

### Lane 1: Probate outbound

- Hermes gathers Harris County probate rows and any tax-delinquency overlay outside Ares
- Ares accepts structured probate intake payloads
- Ares normalizes, scores, and enriches records
- Ares boosts `estate_of + tax_delinquent` style pain stacks when present
- Ares routes eligible leads into Instantly
- Ares ingests Instantly webhooks
- Ares suppresses on reply, bounce, unsubscribe, wrong person, and closed
- Ares creates operator tasks and shows the lane in Mission Control

### Lane 2: Lease-option inbound

- Landing page submits into Ares
- Ares persists contact, conversation, messages, booking state, and sequence state through the repository abstraction in memory / fixtures for this pass; live Supabase wiring is deferred
- Ares handles `Cal.com` booking webhooks and `TextGrid` inbound webhooks idempotently
- Ares schedules and runs the non-booker follow-up sequence through Trigger.dev
- Ares creates operator tasks for manual-call checkpoints and hot/ambiguous replies
- Mission Control shows pending vs booked, active follow-up, replies, and tasks

### Shared downstream seam

- A minimal `opportunities` skeleton exists for:
  - `qualified_opportunity`
  - `offer_path_selected`
  - `under_negotiation`
  - `contract_sent`
  - `contract_signed`
  - `title_open`
  - `curative_review`
  - `dispo_ready`
  - `closed`
  - `dead`

Do not build full TC/title/dispo automation in this slice. Just create the seam.

---

## What already exists and must be reused

### Lease-option inbound slice already in the current branch

- `app/api/marketing.py`
- `app/services/marketing_lead_service.py`
- `app/services/booking_service.py`
- `app/services/inbound_sms_service.py`
- `app/db/contacts.py`
- `app/db/conversations.py`
- `app/db/messages.py`
- `app/db/bookings.py`
- `app/db/sequences.py`
- `app/db/tasks.py`
- `app/db/marketing_supabase.py`
- `supabase/migrations/202604140001_lease_option_marketing_mvp.sql`

### Probate / lead-machine slice already exists on `origin/main`

Prefer porting or cherry-picking these instead of rewriting:

- `bf8db3292e68aec8b81f752bfbf914df88049be9`
- later `origin/main` lead-machine files including:
  - `app/models/probate_leads.py`
  - `app/models/leads.py`
  - `app/models/lead_events.py`
  - `app/models/campaigns.py`
  - `app/models/automation_runs.py`
  - `app/models/suppression.py`
  - `app/db/leads.py`
  - `app/db/lead_events.py`
  - `app/db/campaigns.py`
  - `app/db/campaign_memberships.py`
  - `app/db/automation_runs.py`
  - `app/db/provider_webhooks.py`
  - `app/db/suppression.py`
  - `app/providers/instantly.py`
  - `app/services/harris_probate_intake_service.py`
  - `app/services/probate_hcad_match_service.py`
  - `app/services/probate_lead_score_service.py`
  - `app/services/probate_lead_bridge_service.py`
  - `app/services/lead_outbound_service.py`
  - `app/services/lead_webhook_service.py`
  - `app/services/lead_suppression_service.py`
  - `app/services/lead_task_service.py`
  - `app/services/mission_control_service.py` lead-machine additions
  - `app/api/mission_control.py` lead-machine additions

### Existing generic runtime pieces to keep

- `app/core/config.py`
- `app/db/client.py`
- `app/services/provider_retry_service.py`
- `app/services/provider_preflight_service.py`
- `app/services/mission_control_service.py`
- `apps/mission-control/`

---

## Hard rules for this implementation

- Ares does not scrape Harris County sites or do browser automation
- Hermes or another driver sends structured probate payloads into Ares
- Inbound lease options and outbound probate stay separate in state and routing
- Providers are transport only
- Supabase backend wiring is deliberately delayed for this pass; the current blueprint keeps both live MVP lanes memory / fixture-backed until the later backend cutover
- Memory fallback remains available for tests and fixture-first development
- Do not replace the lease-option lane; harden it
- Do not invent a full business OS here

---

## Data ownership for the MVP

### Shared runtime primitives

Use shared tables and services only where the concepts are truly shared:

- `businesses`
- `contacts`
- `conversations`
- `messages`
- `tasks`
- `provider_webhooks`
- `opportunities`

### Lease-option inbound lane

Keep using the existing marketing slice and persist it through the repository layer in memory / fixtures for this pass:

- `contacts`
- `conversations`
- `messages`
- `booking_events`
- `sequence_enrollments`
- `tasks`
- `provider_webhooks`

### Probate outbound lane

Add lane-specific state for outbound automation:

- `probate_leads`
- `leads`
- `campaigns`
- `campaign_memberships`
- `lead_events`
- `automation_runs`
- `suppressions`
- `provider_webhooks`

### Cross-lane downstream seam

- `opportunities`

This table links either lane into a minimal acquisition pipeline without forcing both lanes into one contact model right now.

---

## Lease-option recommendation for this MVP

Treat lease options as a reliability-hardening track, not a new product branch.

What to do now:

- keep the current submit -> booking -> non-booker -> SMS flow intact
- make every webhook idempotent and persisted
- make sequence guards replay-safe
- record outbound and inbound messages consistently
- improve lead/conversation resolution beyond raw phone-only matching when provider metadata exists
- expose the live lane cleanly in Mission Control

What not to do now:

- no new creative-finance branch logic
- no voice
- no broad multi-lane inbound buildout
- no rewrite of the landing page flow

---

## Task 1: Bring the probate lead-machine slice into the current branch

**Subtasks:**

1. Compare the branch against `origin/main` and identify the exact lead-machine files that already exist upstream.
2. Port the models first, then repositories, then services, then API wiring, so the branch stays runnable at each step.
3. Keep every imported path behind the repository abstraction; do not turn on the deferred Supabase backend path.
4. Port the tests next to the code they cover so each batch has a verification target.
5. Run the imported lead-machine tests in memory mode before moving to Task 4.

**Files to port or create:**

- `app/models/probate_leads.py`
- `app/models/leads.py`
- `app/models/lead_events.py`
- `app/models/campaigns.py`
- `app/models/automation_runs.py`
- `app/models/suppression.py`
- `app/db/leads.py`
- `app/db/lead_events.py`
- `app/db/campaigns.py`
- `app/db/campaign_memberships.py`
- `app/db/automation_runs.py`
- `app/db/provider_webhooks.py`
- `app/db/suppression.py`
- `app/providers/instantly.py`
- `app/services/harris_probate_intake_service.py`
- `app/services/probate_hcad_match_service.py`
- `app/services/probate_lead_score_service.py`
- `app/services/probate_lead_bridge_service.py`
- `app/services/lead_outbound_service.py`
- `app/services/lead_webhook_service.py`
- `app/services/lead_suppression_service.py`
- `app/services/lead_task_service.py`
- related tests from `origin/main`

- [ ] Compare current branch against `origin/main` for the lead-machine files and choose the smallest safe import path
- [ ] Prefer cherry-picking or file-porting over rewriting logic that already exists
- [ ] Preserve the deterministic scoring and webhook/event semantics already present on `origin/main`
- [ ] Add package exports and package-layout coverage where needed
- [ ] Run the imported probate / lead-machine tests and confirm they pass before touching the deferred Supabase wiring

**Acceptance gate:** The current branch has the newer Ares probate and lead-machine services locally, still runnable in memory mode.

---

## Deferred backend wiring pass: Add Supabase schema for the probate outbound lane and the shared downstream seam

> Deferred for this branch pass. Keep this section as the later backend cutover blueprint. Do not apply these migrations, and do not treat this as current work until the user explicitly re-enables backend wiring.

**Files:**

- Create: `supabase/migrations/202604160001_lead_machine_runtime.sql`
- Create: `supabase/migrations/202604160002_runtime_opportunities.sql`
- Modify if needed: existing RLS helper usage to match repo conventions

### Table set for `202604160001_lead_machine_runtime.sql`

- `probate_leads`
- `leads`
- `campaigns`
- `campaign_memberships`
- `lead_events`
- `automation_runs`
- `suppressions`
- `provider_webhooks`

### Table set for `202604160002_runtime_opportunities.sql`

- `opportunities`

### Required schema rules

- every table is tenant-scoped by `(business_id, environment)`
- every table gets `created_at` and `updated_at` where appropriate
- `lead_events`, `automation_runs`, `campaign_memberships`, and `provider_webhooks` get idempotency / replay-safe uniqueness
- `provider_webhooks` is generic enough to store Instantly, `Cal.com`, and `TextGrid` receipts
- `suppressions` supports global and campaign-scoped suppressions
- `opportunities` links to either `lead_id` or `contact_id` plus a lane marker
- use RLS and tenant policies that match the existing marketing migration style

- [ ] Write migration tests or validation queries for the new tables and uniqueness constraints, but keep them in the doc until backend wiring is re-enabled
- [ ] Keep the lead-machine migration with indexes on identity keys, provider ids, and timeline reads as the future backend blueprint
- [ ] Keep the opportunities migration with stage, strategy, title, TC, and dispo status fields intentionally thin for the later cutover
- [ ] Do not apply migrations to the local Supabase project in this pass

**Acceptance gate:** The schema blueprint is fully specified, but live Supabase changes remain untouched in this pass.

---

## Deferred backend wiring pass: Add a dedicated Supabase adapter for the lead-machine lane

> Deferred for this branch pass. Keep the adapter dormant and memory-default. Do not activate or rely on live Supabase in this pass.

**Files:**

- Modify: `app/core/config.py`
- Create: `app/db/lead_machine_supabase.py`
- Modify: `app/db/__init__.py`
- Modify: new lead-machine repositories to support memory + Supabase mode

### Settings change

Add:

- `lead_machine_backend: Literal["memory", "supabase"] = "memory"`
- `instantly_api_key`
- `instantly_base_url` if needed
- `instantly_webhook_secret` if available from the chosen webhook setup

Do not overload `marketing_backend`. Keep lease-option and probate toggles separate.

- [ ] Add the new config fields and env aliases as future backend wiring, but keep the default execution mode memory-backed
- [ ] Create `app/db/lead_machine_supabase.py` mirroring the small helper style used by `app/db/marketing_supabase.py`, but leave it dormant in this pass
- [ ] Keep the new lead-machine repositories running in-memory for tests and fixture work in this pass
- [ ] Keep `provider_webhooks` repository usable by both the outbound lane and the lease-option lane without switching backend modes

**Acceptance gate:** Probate outbound services can run in-memory and fixture-backed without changing the lease-option marketing backend switch.

---

## Task 4: Build the probate outbound write path

**Subtasks:**

1. Add the new API router and mount it in `app/main.py` without disturbing the existing marketing routes.
2. Build the probate intake endpoint first, with tests for accepted payloads, tenant resolution, scoring, and bridge creation.
3. Build the Instantly enqueue endpoint second, with tests for campaign membership creation and outbound run records.
4. Build the Instantly webhook endpoint third, with tests for receipt-first persistence, lead events, suppressions, and task creation.
5. Add Trigger-only async fan-out where durable follow-up work is actually needed; do not add backend persistence here.
6. Run the targeted API/service tests and one end-to-end fixture pass before leaving this task.

**Files:**

- Create: `app/api/lead_machine.py`
- Modify: `app/main.py`
- Modify: `trigger/` tasks or add new lead-machine tasks under the existing Trigger layout
- Reuse: `app/services/harris_probate_intake_service.py`
- Reuse: `app/services/probate_lead_bridge_service.py`
- Reuse: `app/services/lead_outbound_service.py`
- Reuse: `app/services/lead_webhook_service.py`

### Required write endpoints

- `POST /lead-machine/probate/intake`
- `POST /lead-machine/outbound/enqueue`
- `POST /lead-machine/webhooks/instantly`

### Required behavior

- probate intake accepts structured records from Hermes, not raw scraping instructions
- intake persists `probate_leads`, runs normalization/scoring, and bridges eligible records into `leads`
- enqueue sends selected leads to Instantly and records `automation_runs` plus `campaign_memberships`
- webhook ingest records a `provider_webhooks` receipt first, then appends canonical `lead_events`, updates `leads`, applies `suppressions`, and creates tasks
- tax delinquency and `estate_of` overlays must be preserved in the probate payload and score metadata even if Hermes did the enrichment upstream

- [ ] Write failing API and service tests for probate intake, outbound enqueue, and Instantly webhook ingest
- [ ] Implement the router and service composition
- [ ] Add signature verification if Instantly provides a stable webhook secret path; otherwise record trust metadata and keep the receipt idempotency wall
- [ ] Add Trigger jobs for enqueue fan-out and webhook follow-on tasks only where durable async work is needed
- [ ] Run targeted tests and one local end-to-end fixture pass

**Acceptance gate:** Hermes can hand Ares probate records, Ares can enqueue them into Instantly, and replies/suppressions/tasks come back into Ares through a replay-safe path.

---

## Task 5: Harden the lease-option inbound lane

**Subtasks:**

1. Keep the existing submit -> booking -> non-booker flow intact while adding receipt-first webhook persistence.
2. Make duplicate `Cal.com` and `TextGrid` events idempotent before any side effects run.
3. Make outbound confirmations and sequence sends append to `messages` consistently so the timeline is replayable.
4. Tighten the sequence guard logic so booked or manually-paused leads never keep receiving non-booker messages.
5. Improve inbound SMS resolution in order: provider thread metadata, tenant phone match, ambiguity task.
6. Run the existing lease-option tests plus the new idempotency coverage before leaving this task.

**Files:**

- Modify: `app/api/marketing.py`
- Modify: `app/services/marketing_lead_service.py`
- Modify: `app/services/booking_service.py`
- Modify: `app/services/inbound_sms_service.py`
- Modify: `app/db/contacts.py`
- Modify: `app/db/conversations.py`
- Modify: `app/db/messages.py`
- Modify: `app/db/bookings.py`
- Modify: `app/db/sequences.py`
- Modify: `app/db/tasks.py`
- Reuse: `provider_webhooks` repository for webhook receipts

### Hardening goals

- make `Cal.com` and `TextGrid` webhook ingest idempotent
- persist webhook receipts before side effects
- record outbound confirmation and sequence messages into `messages`
- improve inbound SMS resolution:
  - first by provider thread metadata when available
  - then by tenant-scoped phone match
  - then create an operator task if ambiguous
- keep sequence suppression exact when booked, cancelled, opted out, or manually paused
- preserve the existing lease-option flow and copy decisions

- [ ] Write failing tests for duplicate `Cal.com` booking webhooks and duplicate `TextGrid` inbound events
- [ ] Add `provider_webhooks` receipt handling into the lease-option services
- [ ] Make outbound confirmations and sequence steps append `messages`
- [ ] Tighten sequence guard logic so booked leads never continue the non-booker sequence
- [ ] Add an explicit operator-task path for ambiguous replies and unmatched inbound messages
- [ ] Run the existing lease-option tests plus the new idempotency coverage

**Acceptance gate:** The lease-option lane is no longer a best-effort memory flow; it is a persisted, replay-safe inbound machine.

---

## Task 6: Add Mission Control surfaces for both lanes without collapsing them together

**Subtasks:**

1. Extend the Mission Control service layer first so it can return lane-separated read models.
2. Update the API contract next, keeping the outbound probate queue, inbound lease-option queue, and opportunity summary separate.
3. Update the Mission Control frontend last, after the API payloads are stable.
4. Make the UI show lane boundaries clearly instead of merging both workflows into one undifferentiated list.
5. Run typecheck, tests, and build after the UI and API changes land.

**Files:**

- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/api.ts`
- Add or modify focused pages/components for:
  - outbound probate queue
  - outbound reply/suppression timeline
  - inbound lease-option queue
  - thin opportunity board

### Required operator views

- `Lead Machine`
  - outbound probate queue
  - campaign state
  - reply/suppression timeline
  - operator tasks
- `Marketing`
  - new lease-option submissions
  - pending vs booked
  - active non-booker sequence
  - inbound replies needing action
- `Pipeline`
  - minimal opportunity stage board

- [ ] Add or extend backend read models for both lanes
- [ ] Keep the UI additive and dense; do not rewrite the whole shell
- [ ] Make lane boundaries obvious in the UI
- [ ] Run Mission Control typecheck, tests, and build

**Acceptance gate:** One operator can see the outbound probate machine, the inbound lease-option machine, and the minimal downstream pipeline in one cockpit without losing lane separation.

---

## Task 7: Add the minimal contract-to-close skeleton

**Subtasks:**

1. Define the thin opportunity model and repository first, with no title/TC/dispo automation beyond the fields in the plan.
2. Wire the creation points from probate and lease-option into the new service so both lanes can open an opportunity without merging their state.
3. Add Mission Control summaries for opportunity counts and stage transitions only after the service is stable.
4. Keep the opportunity seam memory / fixture-backed in this pass and leave the Supabase cutover for the deferred backend section.
5. Run the opportunity model, repository, and service tests before leaving this task.

**Files:**

- Create: `app/models/opportunities.py`
- Create: `app/db/opportunities.py`
- Create: `app/services/opportunity_service.py`
- Modify: Mission Control read models and tests
- Wire through the repository abstraction and keep the opportunity seam memory / fixture-backed in this pass

### Required fields

- `source_lane`
- `strategy_lane`
- `stage`
- `lead_id` or `contact_id`
- `title_status`
- `tc_status`
- `dispo_status`
- `metadata`

### Required creation points

- probate lead becomes an opportunity when positive reply / interested status is recorded
- lease-option lead becomes an opportunity when booked and qualified, or when an operator marks it ready

- [ ] Write failing tests for opportunity creation and stage updates
- [ ] Implement the model, repository, and service with minimal stage transitions
- [ ] Surface opportunity counts and stage summaries in Mission Control

**Acceptance gate:** The MVP can hand a live prospect into a persisted downstream pipeline abstraction without pretending title, TC, and dispo are finished.

---

## Task 8: Verification and rollout gates

**Subtasks:**

1. Run the backend tests first so you know whether the branch is still sane before touching the frontend checks.
2. Run Mission Control typecheck, tests, and build next.
3. Run Trigger checks for any new lead-machine tasks after the code they depend on exists.
4. Run one fixture smoke test per lane, not a live Supabase smoke test, because backend wiring is deferred in this pass.
5. Confirm the repo starts in memory mode with no live Supabase env required for this slice.

**Checks:**

- [ ] Run backend tests:
  - `uv run pytest -q`
- [ ] Run Mission Control checks:
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run`
  - `npm --prefix apps/mission-control run build`
- [ ] Run Trigger checks for any new lead-machine tasks
- [ ] Run one fixture smoke test for each lane:
  - lease-option submit -> booking webhook -> non-booker guard
  - probate intake -> enqueue -> webhook ingest
- [ ] Verify the repo can start with the required backend toggles left in memory mode and without any live Supabase env required for this pass

---

## Recommended execution order

1. Port the lead-machine slice from `origin/main`
2. Keep the Supabase schema and lead-machine backend adapter as deferred blueprint material only
3. Wire probate outbound write paths
4. Harden the lease-option inbound lane
5. Add Mission Control dual-lane views
6. Add the thin opportunity seam
7. Run full verification

This order keeps us from overbuilding UI or downstream pipeline state before the two live lead loops are actually real, while preserving a later backend cutover plan for Supabase.
