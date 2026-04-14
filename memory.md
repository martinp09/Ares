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
  - Supabase-backed control-plane persistence for commands, approvals, runs, events, artifacts, agents, revisions, sessions, permissions, outcomes, and operational assets when `control_plane_backend=supabase`
  - in-memory fallback store remains for local/default non-Supabase execution and for Mission Control thread projections
- Current workflow coverage:
  - marketing command classification
  - Hermes tool contract with permission-aware tool gating
  - replay safety API
  - Trigger marketing worker chain scaffold
  - landing-page site-event forwarding contract
  - managed-agent revision/session/outcome/asset persistence on the Supabase adapter path

## Hermes Integration

- Hermes handles chat, approvals, coordination, and operator UX
- Hermes should not be treated as the source of truth
- Every Hermes action should map to a typed runtime command

## Migration Strategy

- Start fresh on new Supabase and new runtime repo
- Build marketing control plane first
- Defer seller-ops migration off `n8n` until runtime backbone exists

## Open Work

1. finish Supabase persistence rollout by replacing Mission Control thread state with derived projections from canonical persisted data
2. connect Trigger tasks to runtime run/event/artifact writes
3. push the clean control-plane schema baseline after final schema review
4. align operator docs across `Hermes Central Command` and `Mailers AWF`
5. start QC and devil's-advocate review loop after code/docs settle

## Change Log

### 2026-04-13 Managed-Agent Supabase Adapter Slice 4 (Agents/Sessions/Permissions/Outcomes/Assets)

- Implemented Supabase-backed repository behavior in `app/db/agents.py` and `app/db/sessions.py`, preserving runtime text IDs, revision pinning, archived-revision guards, and append-only session timelines behind `control_plane_backend=supabase`
- Added additive migrations `supabase/migrations/202604130004_managed_agent_persistence_tables.sql` and `supabase/migrations/202604130005_managed_agents_sessions_persistence.sql` for permissions, outcomes, operational assets, agents, revisions, sessions, and session events without rewriting prior schema
- Added focused Supabase adapter tests for managed agents/sessions and expanded persistence/API coverage for permissions, outcomes, and agent assets
- Verified Python test suite health with `uv run pytest -q` (`89 passed`)
- Verified local Supabase apply loop on this machine with Colima using `supabase start --exclude vector --exclude logflare`, `supabase db reset --local`, `supabase stop`, and `colima stop`

### 2026-04-13 Runtime-Core Supabase Adapter Slice 3 (Commands/Approvals/Runs/Events/Artifacts)

- Replaced the `SupabaseControlPlaneClient` placeholder with real REST helpers in `app/db/client.py` (`select`, `insert`, `update`) while retaining memory transaction fallback for non-runtime-core repositories
- Implemented Supabase-backed repository behavior in `app/db/commands.py`, `app/db/approvals.py`, `app/db/runs.py`, `app/db/events.py`, and `app/db/artifacts.py` with runtime-ID-first mapping and no schema expansion beyond migration `202604130002`
- Added explicit repository persistence methods (`save`) for command and run state transitions, then updated runtime-core services (`command`, `approval`, `run`, `replay`, `run_lifecycle`) to persist transitions without relying on in-memory object mutation side effects
- Fixed run row mapping so `replay_source_runtime_id` is preserved distinctly from `parent_runtime_id` when both are present
- Added focused Supabase adapter tests in `tests/db/test_runtime_supabase_adapter.py` and expanded run mapping coverage in `tests/db/test_runs_repository.py`
- Verified branch health with `uv run pytest -q` (`74 passed`)

### 2026-04-13 Supabase Local Environment Workaround (Colima Socket Mount)

- Reproduced local `supabase start` failure after migrations with Colima Docker context: `error while creating mount source path '/Users/solomartin/.colima/default/docker.sock': ... operation not supported`
- Confirmed failure is environment-level socket bind-mount behavior, not migration/runtime persistence logic
- Validated repeatable local loop on this machine using:
  - `supabase start --exclude vector --exclude logflare`
  - `supabase db reset --local`
  - `supabase stop`
- Verified cleanup path:
  - `supabase stop` leaves no `supabase_*Hermes_Central_Command` containers running
  - `colima stop` shuts down Docker daemon/VM for zero-background-process state

### 2026-04-13 Persistence Compatibility Slice 2 (Repo + Migration Seam)

- Added additive migration `supabase/migrations/202604130002_mission_control_runtime_persistence.sql` to introduce runtime compatibility columns and indexes for commands, approvals, runs, events, and artifacts without rewriting the baseline schema
- Added repository-only SQL/runtime mapping seams in `app/db/*` for command status and policy drift, approval decided/actor drift, run status and lineage drift, and runtime ID row builders for events and artifacts
- Added in-memory runtime-to-SQL identity bookkeeping in `app/db/client.py` so repository behavior matches the forthcoming SQL adapter shape
- Normalized the remaining runtime-core and request-edge tests to integer `business_id` while explicitly keeping Mission Control read-model business IDs string-backed at the response boundary for now
- Verified the branch with `uv run pytest -q` (`70 passed`); local `supabase db reset --local` remains unverified on this machine because Docker was unavailable during worker execution

### 2026-04-13 Persistence Freeze Slice 1 (Runtime Contracts)

- Froze `business_id` to canonical integer on runtime command, approval, and run contracts in `app/models/commands.py`, `app/models/approvals.py`, and `app/models/runs.py`
- Added `replay_source_run_id` to run contracts and defaulted it to `parent_run_id` when replay lineage exists
- Updated and passed focused API contract tests for commands, approvals, runs, and replays with integer `business_id` payloads
- Broad API test run flagged remaining non-slice tests that still submit string `business_id` on Hermes tools, Mission Control, and Trigger callback paths

### 2026-04-13 Supabase Persistence Design Pass

- Added `docs/superpowers/plans/2026-04-13-mission-control-supabase-persistence-plan.md` as the dedicated design-only rollout plan for the later Supabase persistence branch
- Froze the safety rules for the persistence pass: additive migrations only, local reset first, preview or staging before production, and no mixed contract plus persistence deploys
- Expanded the in-memory replacement scope to cover commands, approvals, runs, events, artifacts, agents, revisions, sessions, permissions, outcomes, assets, and Mission Control read models
- Called out the major schema risks up front, especially Python string IDs versus bigint SQL baseline IDs and status-field drift between models and migrations

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
