# Memory

> This is the master memory file. Keep it indexed and durable. Do not load the whole file by default.

## How To Use This File

- Start in `CONTEXT.md`
- Read only the sections referenced there unless the task clearly requires more
- Record durable architecture decisions, environment notes, open work, and major change history here

## Memory Index

- Current priorities:
  - `## Current Direction`
  - `## Open Work`
- Repo conventions:
  - `## Repo Conventions`
- Environment and infra:
  - `## Environment Notes`
- Architecture:
  - `## Runtime Architecture`
  - `## Hermes Integration`
- Migration:
  - `## Migration Strategy`
- Recent work:
  - latest entry in `## Change Log`

## Current Direction

- Hermes is the control shell
- This repo is the deterministic runtime
- Generalist core comes before industry-specific packs
- Real estate is the first optimization target
- Marketing control plane is the first execution domain
- The immediate MVP is lease-option marketing, not research/copy generation
- The live path is lead submit -> booking check -> confirmations -> non-booker SMS sequence -> inbound qualification
- Current work is the enterprise-platform backlog, with the no-Supabase dogfood slice already finalized and the next slice set to enterprise controls
- Mission Control stays fixture-backed on this machine until live backend wiring is intentionally enabled later
- The host-adapter/skill seam is now in-memory and additive, with trigger_dev as the default enabled adapter; dispatch requires published revisions and preserves per-revision host adapter config
- Phase-0 docs now lock the product model: agents are the product unit, skills are reusable procedures, host runtimes are adapters, and Mission Control is the operator cockpit
- Ralph loop is now the master execution plan for the remaining phases, with `gpt-5.3-codex` as the work model

## Repo Conventions

- `memory.md` is the master memory
- `CONTEXT.md` stays short and points into this file
- `WAT_Architecture.md` defines the operating model
- Keep hard guarantees in code, not in prompts

## Environment Notes

- Fresh Supabase project created for Hermes Central Command
- Local `.env` should be ported from the validated `Mailers AWF` environment as needed
- GitHub owner: `martinp09`
- Planned local path: `/Users/solomartin/Projects/Hermes Central Command`
- Trigger.dev CLI login is configured on this machine
- `TRIGGER_SECRET_KEY` is present in the local `.env`
- Trigger.dev local worker boot verified against project `proj_puouljyhwiraonjkpiki`
- Local `.env` already includes `Cal.com`, `TextGrid`, and `Resend` credentials needed for the lease-option MVP
- The active landing page lives at `/Users/solomartin/Business/website/lease-options-landing`
- The landing page currently persists form submissions and redirects to `Cal.com`, but still hands automation off to `n8n`
- A proven `TextGrid` adapter exists in `/Users/solomartin/Projects/Phone System/api/_lib/providers/textgrid.js`

## Runtime Architecture

- FastAPI runtime for typed commands and policy
- Trigger.dev for durable jobs
- Supabase for canonical state and audit
- Hermes-facing tool/API surface

## Current Runtime Surface

- FastAPI routes currently mounted:
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
  - `GET /mission-control/lead-machine`
  - `GET /mission-control/inbox`
  - `GET /mission-control/tasks`
  - `GET /mission-control/runs`
  - `POST /marketing/webhooks/calcom`
  - `POST /marketing/webhooks/textgrid`
  - `POST /marketing/internal/non-booker-check`
  - `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
  - `POST /site-events`
  - `POST /trigger/callbacks/runs/{run_id}/started`
  - `POST /trigger/callbacks/runs/{run_id}/completed`
  - `POST /trigger/callbacks/runs/{run_id}/failed`
  - `POST /trigger/callbacks/runs/{run_id}/artifacts`
- Current storage mode:
  - in-memory control-plane store for commands, approvals, runs, site events, agents, revisions, sessions, permissions, outcomes, operational assets, lead-machine state, marketing state, and opportunities
- Current workflow coverage:
  - marketing command classification
  - Hermes tool contract with permission-aware tool gating
  - replay safety API
  - Trigger marketing worker chain scaffold
  - landing-page site-event forwarding contract
  - managed-agent revision/session/outcome/asset scaffolding without live Supabase wiring
  - probate intake -> scoring -> bridge -> enqueue -> webhook -> suppression/task loop
  - lease-option submit -> booking webhook -> SMS/manual-call loop
  - additive Mission Control workspaces for `Lead Machine`, `Marketing`, and `Pipeline`

## Hermes Integration

- Hermes handles chat, approvals, coordination, and operator UX
- Hermes should not be treated as the source of truth
- Every Hermes action should map to a typed runtime command

## Migration Strategy

- Start fresh on new Supabase and new runtime repo
- Build marketing control plane first
- Defer seller-ops migration off `n8n` until runtime backbone exists

## Open Work

1. execute `docs/superpowers/plans/2026-04-20-ralph-loop-full-implementation-plan.md`
2. keep the source docs from the Ralph plan as reference inputs, not separate live targets
3. keep the broader Ares enterprise platform backlog archived until the next explicit reopen
4. continue using the repo-root TODO as the live handoff pointer instead of ad hoc chat notes

## Change Log

### 2026-04-20 Ralph Loop Master Plan

- Added `docs/superpowers/plans/2026-04-20-ralph-loop-full-implementation-plan.md` as the master execution plan for the remaining enterprise-platform phases
- Repointed the repo-root TODO and context files at the Ralph loop plan as the live handoff target
- Kept the older Instantly/probate/curative-title docs as source inputs under the new master plan

### 2026-04-16 Agent API + Session Fixture Cleanup

- Repaired remote Supabase migration history on project `awmsrjeawcxndfnggoxw` and applied:
  - `202604160001_lead_machine_runtime.sql`
  - `202604160002_runtime_opportunities.sql`
- Corrected the live lease-option booking schema to allow `booked` events and verified the lane against remote Supabase:
  - `POST /marketing/leads` -> `201`
  - `POST /marketing/internal/non-booker-check` -> `200`
  - `POST /marketing/webhooks/calcom` -> `200`
  - remote evidence in `contacts`, `booking_events`, `sequence_enrollments`, and `provider_webhooks`
- Verified the probate outbound lane against remote Supabase with a stubbed Instantly transport:
  - `POST /lead-machine/probate/intake` -> `201`
  - `POST /lead-machine/outbound/enqueue` -> `200`
  - `POST /lead-machine/webhooks/instantly` -> `200`
  - remote evidence in `probate_leads`, `leads`, `automation_runs`, `campaign_memberships`, `provider_webhooks`, `lead_events`, `suppressions`, and `opportunities`
- Fixed several Supabase adapter seams uncovered by the live smoke pass:
  - lead-machine migration composite-tenant uniqueness ordering
  - lease-option booking event constraint mismatch (`booked` vs `created`)
  - Supabase rehydration for `probate_leads`, `leads`, `campaign_memberships`, `provider_webhooks`, `lead_events`, and `suppressions`
  - `automation_runs` Supabase insert excluding runtime-only `deduped`
  - campaign active-tenant guard accepting slug requests for numeric Supabase-backed campaigns
  - webhook lead resolution preferring direct email matches so replies attach to the routed probate lead
- Verified repo state after the fixes with `177 passed` backend tests via `./.venv/bin/python -m pytest -q`

### 2026-04-16 MVP Runtime Execution Pass

- Finished the probate outbound write path with:
  - typed `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
- Added `ProbateLeadsRepository` plus canonical `probate_leads` persistence in the intake flow
- Extended probate records to preserve `tax_delinquent`, `estate_of`, and `pain_stack`
- Tightened lead-machine API validation so malformed intake rows and malformed webhook payloads fail with `422` instead of leaking through as `500` / false-positive `200`
- Added the thin opportunity seam in live runtime paths:
  - probate positive reply / interested events create or update probate opportunities
  - first-time booked lease-option contacts create or update lease-option opportunities
- Fixed opportunity identity so records dedupe by `source_lane + identity`, preventing probate and lease-option rows from collapsing together
- Added additive Mission Control surfaces:
  - backend `GET /mission-control/lead-machine`
  - frontend workspaces for `Lead Machine`, `Marketing`, and `Pipeline`
- Verified the repo state with:
  - `168 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - Mission Control `typecheck`, `vitest --run`, and `vite build`
  - Trigger `typecheck`

### 2026-04-16 Mission Control Lane Separation Backend Acceptance

- Added backend Mission Control coverage proving the operator dashboard keeps lease-option marketing counts, additive probate lead-machine counts, and persisted opportunity pipeline summaries separate
- Added an additive `lead_machine_summary` dashboard read model for probate outbound counts without changing the existing marketing inbox/tasks surfaces
- Tightened opportunity stage summaries so they are grouped by both `source_lane` and `stage`, preventing probate and lease-option pipeline rows from collapsing together

### 2026-04-16 Opportunity Creation Wiring Pass

- Wired `OpportunityService` into the live probate webhook path so positive reply and interested events create or update a probate opportunity record
- Wired `OpportunityService` into the live lease-option booking path so first-time booked contacts create or update a lease-option inbound opportunity record
- Added focused service tests covering the probate opportunity trigger and the lease-option booked-contact opportunity trigger

### 2026-04-16 Combined MVP Implementation Plan

- Added `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
- Locked tonight's MVP as a two-lane cut:
  - probate outbound via Instantly cold email
  - lease-option inbound via the existing marketing flow
- Decided to reuse the existing lease-option marketing slice in this branch and bring the newer probate / lead-machine slice forward from `origin/main`
- Decided to wire Supabase as the canonical backend for both live MVP lanes instead of deferring live persistence again
- Chose a shared-runtime split:
  - lease-option keeps its existing marketing objects
  - probate gets lane-specific lead-machine tables
  - both lanes share provider webhook receipts, tasks, Mission Control, and a thin `opportunities` seam

### 2026-04-16 Real Estate Runtime Thesis

- Added `docs/superpowers/specs/2026-04-16-ares-real-estate-runtime-thesis-design.md`
- Locked the product direction: Ares is the reusable runtime, not the main agent
- Chose the long-term domain map: data gathering, prospecting, acquisitions, transaction coordination, title, and dispo
- Chose the architecture split:
  - source lanes describe where an opportunity came from
  - strategy lanes describe how the opportunity may be solved or monetized
  - operational stages describe where the record is in the business process
- Locked the current MVP shape:
  - source lane = probate
  - outbound method = cold email
  - downstream skeleton = thin contract-to-close placeholders for title, TC, and dispo
- Confirmed that tax distress and estate signals should become composite pain-stack inputs, especially `estate_of + tax_delinquent`

### 2026-04-14 Lease-Option Marketing Wiring Pass

- Replaced the landing-page `n8n` handoff with Hermes lead-ingress payloads while keeping the old `n8n` helper type-compatible for legacy tests
- Wired `MarketingLeadService` to configured `TextGrid`, `Resend`, `Cal.com` booking URLs, and Trigger HTTP scheduling instead of the earlier no-op defaults
- Wired booking confirmations, manual-call task persistence, and sequence-step outbound dispatch onto the current in-memory marketing repositories
- Added exact-config support for local env names already present on Martin's machine, including `Cal_API_key` and Trigger settings
- Added webhook-signature enforcement seams for `Cal.com` and `TextGrid` using request details from the FastAPI routes
- Verified current repo state with `95` backend tests passing, Mission Control tests/build passing, Trigger typecheck passing, and landing-page tests/build passing
- Added a marketing-only Supabase adapter layer and verified a live smoke insert into remote `public.contacts` for `limitless/dev`
- Applied the core and lease-option marketing migrations to Supabase project `awmsrjeawcxndfnggoxw` and seeded `public.businesses` with `limitless/dev`
- Kept the repo honest about the remaining MVP risks: inbound SMS matching is still phone-only and sequence guard state is still derived too simplistically for a multi-tenant or more advanced sequence rollout

### 2026-04-14 Lease-Option Marketing MVP Design

- Added `docs/superpowers/specs/2026-04-14-lease-option-marketing-mvp-design.md` as the live marketing MVP design
- Locked the first live scope to lease-option sellers with `45+ DOM` messaging
- Chose `Cal.com` for booking, `TextGrid` for SMS, and `Resend` for transactional email
- Chose the lead-state rule: submit creates `pending`, booking flips to `booked`, and only non-bookers after 5 minutes enter the 10-day intensive
- Chose Hermes to replace the current landing-page `n8n` handoff so booking state, sequence state, inbound replies, and manual-call tasks live in one control plane

### 2026-04-13 Mission Control Finish Plan

- Added `docs/superpowers/plans/2026-04-13-mission-control-finish-plan.md` to separate safe branch completion from later Supabase persistence work
- Captured the recommended rollout order: finish backend/frontend Mission Control contract first, then do additive Supabase migrations in a separate gated pass
- Noted that the branch can be finished without immediate schema changes because the current blocking work is contract alignment, not persistence

### 2026-04-13 Mission Control Docs Sync

- Updated README, CONTEXT, memory, and Mission Control planning/spec docs to reflect the phase-6 landed read models and native shell
- Corrected stale repo-root references in the orchestration plan
- Kept the current phase focus on docs/release-gate cleanup while Supabase persistence remains deferred

### 2026-04-13 Mission Control Frontend Shell

- Added `apps/mission-control/` as a minimal React/TypeScript Mission Control app scaffold with a dense native shell, dashboard, inbox, approvals, runs, agents, and settings/assets surfaces
- Added a typed Mission Control API client, tiny query cache helper, and local fixtures so the UI remains buildable and testable without live Supabase or live backend coupling
- Added Vite/Vitest/TypeScript setup plus targeted UI tests covering shell navigation/search rendering and dashboard count rendering from fixture data

### 2026-04-12 Repo Bootstrap

- Created the clean `Hermes Central Command` repo path
- Confirmed a fresh Supabase project is reachable
- Confirmed migration dry-run access works against the new project
- Ported WAT and memory/context operating conventions into the new repo
- Added Trigger.dev bootstrap files and verified `trigger:dev` reaches a ready local worker
- Added `CODEX.md` with subagent orchestration and cleanup rules

### 2026-04-13 Managed-Agent Scaffold Phase 5

- Added in-memory managed-agent scaffolding for versioned agents, revisions, sessions, tool permissions, outcomes, and connect-later operational assets
- Added FastAPI routes for agents, sessions, permissions, outcomes, and agent assets
- Updated Hermes tools to respect explicit `always_allow`, `always_ask`, and `forbidden` permission policies without adding live Supabase wiring
- Added a scaffold-only Supabase migration placeholder for the deferred managed-agent schema seam
- Added targeted API and package-layout tests covering the new phase-5 surface

### 2026-04-13 Mission Control Read Models

- Added scaffold-first Mission Control read models for dashboard, inbox, and run lineage backed only by the in-memory control-plane store
- Added protected FastAPI routes for `/mission-control/dashboard`, `/mission-control/inbox`, and `/mission-control/runs`
- Added targeted API and package-layout tests covering dashboard counts, seeded inbox threads, and replay lineage with `parent_run_id`

### 2026-04-13 Control Plane Foundation

- Added typed command, approval, run, replay, and site-event runtime models
- Added FastAPI routes for commands, approvals, runs, replays, Hermes tools, and site events
- Added in-memory services to support idempotent command ingestion and replay safety
- Added Trigger.dev marketing worker chain scaffold in `trigger/`
- Added landing-page site-event forwarding plus runtime ingestion tests
