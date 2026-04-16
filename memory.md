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

## Repo Conventions

- `memory.md` is the master memory
- `CONTEXT.md` stays short and points into this file
- `WAT_Architecture.md` defines the operating model
- Keep hard guarantees in code, not in prompts

## Environment Notes

- Fresh Supabase project created for Ares
- Local `.env` should be ported from the validated `Mailers AWF` environment as needed
- GitHub owner: `martinp09`
- Planned local path: `/Users/solomartin/Projects/Ares`
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
  - `GET /mission-control/inbox`
  - `GET /mission-control/runs`
  - `POST /site-events`
  - `POST /trigger/callbacks/runs/{run_id}/started`
  - `POST /trigger/callbacks/runs/{run_id}/completed`
  - `POST /trigger/callbacks/runs/{run_id}/failed`
  - `POST /trigger/callbacks/runs/{run_id}/artifacts`
- Current storage mode:
  - in-memory control-plane store for commands, approvals, runs, site events, agents, revisions, sessions, permissions, outcomes, and operational assets
- Current workflow coverage:
  - marketing command classification
  - Hermes tool contract with permission-aware tool gating
  - replay safety API
  - Trigger marketing worker chain scaffold
  - landing-page site-event forwarding contract
  - managed-agent revision/session/outcome/asset scaffolding without live Supabase wiring

## Hermes Integration

- Hermes handles chat, approvals, coordination, and operator UX
- Hermes should not be treated as the source of truth
- Every Hermes action should map to a typed runtime command

## Migration Strategy

- Start fresh on new Supabase and new runtime repo
- Build marketing control plane first
- Defer seller-ops migration off `n8n` until runtime backbone exists

## Open Work

1. execute `docs/superpowers/specs/Hermes — Instantly Lead Automation Final Spec 2026.md`
2. execute `docs/superpowers/plans/2026-04-16-harris-probate-keep-now-ingestion-plan.md`
3. execute `docs/superpowers/plans/2026-04-16-curative-title-cold-email-machine-plan.md`
4. keep the broader Ares enterprise platform backlog archived until the next explicit reopen
5. continue using the repo-root TODO as the live handoff pointer instead of ad hoc chat notes

## Change Log

### 2026-04-16 Agent API + Session Fixture Cleanup

- Translated create-agent `ValueError` failures to HTTP 422 at the API boundary so unknown skill bindings surface as validation errors instead of uncaught exceptions
- Aligned the session and turn API fixtures to the owned `limitless/dev` agent scope so the session-scoped contract tests exercise the intended happy path

### 2026-04-16 Phase 1 Org Tenancy Turn-Loop Plumbing

- Threaded actor-context org scoping through the `/agents`, session turn-loop, and Mission Control turns routes while preserving the default internal org fallback when headers are absent
- Persisted `org_id` on sessions and turns, exposed `org_id` on Mission Control turn summaries, and filtered Mission Control turn read models to the caller org
- Verified with `pytest -q tests/api/test_turn_loop_contract.py -q` and a focused regression slice covering sessions, turns, compaction, Mission Control turns, and turn-event replay

### 2026-04-16 Claude Code Support Skills Pass

- Installed Hermes-native skills for Claude Code memory, settings, MCP, startup flags, and feature discovery so future sessions can route config questions to the right reusable skill instead of re-deriving the same guidance

### 2026-04-15 No-Supabase Dogfood Slice Finalized

- Closed the no-Supabase dogfood slice with the remaining seam fixes: host adapter config now flows from agent revision to dispatch record, published revisions are required for execution, and Mission Control agents are filtered by business/environment scope
- Kept Mission Control fixture-backed and agent-first while live persistence remains deferred
- Verified the branch again with `uv run pytest -q`, `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run build`, and `git diff --check` all passing

### 2026-04-15 No-Supabase Dogfood Slice

- Locked the current job to the non-Supabase subset of the Ares enterprise platform plan
- Added missing runtime settings for `marketing_backend`, `cal_webhook_secret`, and `textgrid_webhook_secret`
- Fixed Mission Control read models to derive booking/reply/task state from thread context when the top-level fields are empty
- Added a lean in-memory host-adapter/skill seam with `trigger_dev` as the default enabled adapter and `codex` / `anthropic` disabled
- Made Mission Control more agent-first with a fixture-backed Agents cockpit summary and updated shell/navigation copy
- Added phase-0 product-model docs and wiki pages so the platform language is explicit
- Kept the Mission Control cockpit fixture-backed and agent-first while live persistence remains deferred

### 2026-04-15 Enterprise Agent Platform Plan

- Added `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- Captured a phased rollout to turn Ares into an enterprise agent platform with internal dogfood first, enterprise controls second, and marketplace distribution last
- Locked the core product rules in planning: agents are the primary product unit, skills are reusable procedures, Mission Control is the operator cockpit, and host runtimes must stay adapter-based with Trigger.dev swappable for later Codex or Anthropic runtimes

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

- Created the clean `Ares` repo path
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
