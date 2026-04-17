---
title: "Probate Outbound + Lease-Option Inbound MVP Implementation Plan"
status: active
updated_at: "2026-04-16T22:04:50-05:00"
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

Both lanes must run through Ares as the deterministic runtime, keep Hermes as the browser/research driver, and persist live state in Supabase. The broader business OS stays out of scope for this pass, but the MVP must leave a thin contract-to-close seam so acquisitions, title, TC, and dispo can attach later.

**Architecture:** Keep the lanes separate in domain state and operator surfaces. Reuse the existing lease-option marketing slice already in this branch. Bring the newer probate / lead-machine slice forward from `origin/main` instead of rebuilding it. Share only the runtime primitives that should truly be shared: tenant resolution, provider webhook receipts, tasks, Mission Control read models, and a minimal downstream opportunity skeleton.

**Tech Stack:** FastAPI, Pydantic, pytest, Trigger.dev, Supabase REST wiring, existing Mission Control app, existing lease-option provider adapters, Instantly API v2, and Hermes as the upstream browser-capable driver.

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
- Ares persists contact, conversation, messages, booking state, and sequence state in Supabase
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
- Supabase becomes the canonical store for both live MVP lanes
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

Keep using the existing marketing slice and persist it in Supabase through:

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
- [ ] Run the imported probate / lead-machine tests and confirm they pass before touching Supabase wiring

**Acceptance gate:** The current branch has the newer Ares probate and lead-machine services locally, still runnable in memory mode.

---

## Task 2: Add Supabase schema for the probate outbound lane and the shared downstream seam

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

- [ ] Write migration tests or validation queries for the new tables and uniqueness constraints
- [ ] Implement the lead-machine migration with indexes on identity keys, provider ids, and timeline reads
- [ ] Implement the opportunities migration with stage, strategy, title, TC, and dispo status fields kept intentionally thin
- [ ] Apply migrations to the local Supabase project and verify schema creation

**Acceptance gate:** Supabase contains the outbound lead-machine tables plus the minimal downstream opportunity seam, without disturbing the existing lease-option marketing schema.

---

## Task 3: Add a dedicated Supabase adapter for the lead-machine lane

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

- [ ] Add the new config fields and env aliases
- [ ] Create `app/db/lead_machine_supabase.py` mirroring the small helper style used by `app/db/marketing_supabase.py`
- [ ] Wire the new lead-machine repositories so they support in-memory tests and live Supabase mode
- [ ] Keep `provider_webhooks` repository usable by both the outbound lane and the lease-option lane

**Acceptance gate:** Probate outbound services can run against Supabase without changing the lease-option marketing backend switch.

---

## Task 4: Build the probate outbound write path

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

**Files:**

- Create: `app/models/opportunities.py`
- Create: `app/db/opportunities.py`
- Create: `app/services/opportunity_service.py`
- Modify: Mission Control read models and tests
- Wire to Supabase through `opportunities`

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

**Acceptance gate:** The MVP can hand a live prospect into a persisted downstream pipeline without pretending title, TC, and dispo are finished.

---

## Task 8: Verification and rollout gates

- [ ] Run backend tests:
  - `uv run pytest -q`
- [ ] Run Mission Control checks:
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run`
  - `npm --prefix apps/mission-control run build`
- [ ] Run Trigger checks for any new lead-machine tasks
- [ ] Run one Supabase smoke test for each lane:
  - lease-option submit -> booking webhook -> non-booker guard
  - probate intake -> enqueue -> webhook ingest
- [ ] Verify the repo can start with the required backend toggles and provider env vars set

---

## Recommended execution order

1. Port the lead-machine slice from `origin/main`
2. Add Supabase schema and the lead-machine backend adapter
3. Wire probate outbound write paths
4. Harden the lease-option inbound lane
5. Add Mission Control dual-lane views
6. Add the thin opportunity seam
7. Run full verification

This order keeps us from overbuilding UI or downstream pipeline state before the two live lead loops are actually real.
