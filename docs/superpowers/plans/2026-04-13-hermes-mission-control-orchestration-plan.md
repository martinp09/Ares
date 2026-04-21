# Hermes Mission Control Blueprint and Implementation Plan

> Execution root: `/root/.config/superpowers/worktrees/Hermes-Central-Command/mission-control-enterprise-backlog`
>
> Use this blueprint exactly in order. Do not start a later phase early. Do not back-edit an earlier phase unless that earlier file is explicitly listed in the current phase. Every phase ends with an exit gate; do not continue until that gate passes.

## Blueprint Summary

Hermes Mission Control is a native control plane inside Ares, not a separate product and not a parallel orchestration stack.

This blueprint turns the current repo from a thin runtime skeleton into a full control-plane system with explicit wiring:
- FastAPI remains the typed policy boundary and runtime API surface.
- Supabase/Postgres becomes the canonical persistence and read-model layer.
- Trigger.dev becomes the durable execution engine for queued work, retries, concurrency, and replay timing.
- Claude Managed Agents becomes the source of agent-session-permission-rubric patterns, not a replacement for Trigger.dev.
- GoHighLevel contributes only draft/production ergonomics, clone/template ergonomics, and connect-later asset binding.

The blueprint is intentionally narrow:
- no second scheduler
- no second queue engine
- no visual canvas
- no page builder
- no landing page composer
- no website builder

## Current Baseline vs Target Mission Control Shape

The current branch already has most of the control plane in place, with the remaining work concentrated on docs sync, release-gate cleanup, and later Supabase wiring.

Current baseline:
- `app/` contains the FastAPI runtime and typed routes.
- `app/services/run_service.py` still uses process-local runtime state through the in-memory `STORE` container, with repository seams under `app/db/`.
- `app/services/mission_control_service.py` and `apps/mission-control/` now provide the phase-6 Mission Control read models and native cockpit shell.
- `trigger/src/marketing/runMarketResearch.ts`, `trigger/src/marketing/createCampaignBrief.ts`, `trigger/src/marketing/draftCampaignAssets.ts`, and `trigger/src/marketing/assembleLaunchProposal.ts` remain the marketing execution scaffold.
- `supabase/migrations/202604130001_hermes_control_plane_core.sql` and `supabase/migrations/202604130003_mission_control_managed_agents.sql` establish the database direction and managed-agent schema seam.
- The current Hermes tool layer is still a projection of hard-coded command policy rather than a durable registry.

Target shape:
- every command, approval, run, artifact, and event is durably recorded in Supabase.
- FastAPI owns the policy boundary, state transitions, and tenant-scoped contract enforcement.
- Trigger.dev receives runtime-issued execution envelopes, not ad hoc worker payloads.
- Trigger.dev reports lifecycle facts back into runtime-owned records through an explicit callback/update boundary.
- the UI and any operator views consume stable runtime read models rather than worker internals.
- the agent/tool registry becomes data-backed and revisioned.
- replay and lineage are runtime-owned concepts, not worker-owned side effects.

## End-to-End Wiring Map

The clean mental model for the system is:
1. an operator or Hermes-visible tool submits a command to FastAPI.
2. FastAPI classifies the command, applies policy, and writes the canonical record.
3. If approval is required, FastAPI creates an approval record and stops at the runtime boundary.
4. If execution is allowed, FastAPI creates a runtime run record and prepares a Trigger.dev execution envelope.
5. Trigger.dev executes the durable workflow and any marketing/domain stage chain.
6. Trigger.dev or a runtime callback endpoint writes lifecycle facts back into Supabase through FastAPI-owned services.
7. FastAPI surfaces run state, artifacts, approvals, and replay lineage from Supabase-backed read models.
8. The UI renders those read models; it does not own the source of truth.

The blueprint should make this wiring explicit:
- Hermes/operator surface: command submission and tool discovery.
- FastAPI: command policy, approval gating, run orchestration, replay creation, lifecycle persistence.
- Supabase/Postgres: canonical state, read models, tenant scoping, RLS, append-only events.
- Trigger.dev: durable execution, retries, concurrency, and step-level worker logic.
- UI: timelines, run detail, approvals inbox, artifacts, and replay views.

## Repository Ownership Map

Each area of the repo should have one obvious job so later Codex passes do not have to infer boundaries.

- `app/main.py`
  - service composition and router mounting
  - top-level runtime boundaries

- `app/core/config.py`
  - environment settings
  - runtime API keys
  - Supabase connection settings
  - feature toggles that are truly runtime-wide

- `app/core/dependencies.py`
  - request authentication and runtime dependency wiring
  - bearer-key gate for protected endpoints

- `app/api/commands.py`
  - command ingestion and immediate policy response

- `app/api/approvals.py`
  - approval create/approve/deny boundaries

- `app/api/runs.py`
  - runtime run detail and status lookup

- `app/api/replays.py`
  - replay requests and replay lineage read/write

- `app/api/hermes_tools.py`
  - Hermes-visible tool discovery and invocation surface

- `app/api/site_events.py`
  - site-event ingestion boundary

- `app/api/marketing.py`
  - deterministic marketing/domain stage handlers used by workers

- new `app/api/trigger_callbacks.py`
  - worker-to-runtime lifecycle update boundary

- `app/services/command_service.py`
  - command ingestion, dedupe, and initial state transitions

- `app/services/approval_service.py`
  - approval record creation and transition logic

- `app/services/run_service.py`
  - run creation/read logic
  - should stop being a process-local source of truth

- `app/services/replay_service.py`
  - runtime replay branching and lineage logic

- new `app/services/run_lifecycle_service.py`
  - canonical event ingestion from Trigger callbacks
  - run/task/artifact/event updates

- new `app/services/agent_registry_service.py`
  - revisioned agent/tool registry resolution

- `app/models/*`
  - typed contracts for commands, approvals, runs, tasks, artifacts, events, contacts, conversations, and future managed-agent shapes

- `app/db/*`
  - persistence client and repository abstractions

- `trigger/src/shared/runtimeApi.ts`
  - shared runtime POST helper for worker-to-runtime calls

- `trigger/src/marketing/*`
  - the existing durable stage chain that Trigger runs today

- `supabase/migrations/202604130001_hermes_control_plane_core.sql`
  - the canonical database baseline that later phases extend

- `tests/*`
  - API, policy, domain, and persistence verification

## What This Blueprint Expands Beyond the Baseline

This is the part that makes the document a blueprint instead of only a task list.

The current repo already has a strong skeleton, but the vision moves it forward by adding:
- durable orchestration state instead of process-local state
- runtime-owned transition records instead of implicit flow
- worker callbacks into runtime-owned lifecycle records
- runtime-issued envelopes that carry tenant and revision metadata
- registry-backed Hermes tools instead of hard-coded policy tables
- stable operator read models instead of direct worker inspection
- explicit replay and lineage semantics instead of ad hoc reruns
- agent/session/permission/rubric concepts as first-class runtime data

That means the blueprint is not “build something new from scratch”; it is “harden the existing control plane into a true mission-control layer without breaking the current repo’s direction.”

## Canonical Wiring Contracts

These are the non-negotiable contracts that later implementation passes must keep intact.

- Tenant contract
  - canonical scope is `business_id + environment`
  - the same tenant key must appear in Python models, database rows, Trigger payloads, and UI filters
  - any type mismatch between app models and SQL must be resolved before runtime repositories are finalized

- Idempotency contract
  - the runtime owns command dedupe and run creation dedupe
  - Trigger.dev should not become the source of truth for idempotency
  - replay gets a distinct lineage strategy and should not reuse the original command identity

- Run correlation contract
  - runtime `run_id` is the primary control-plane identity
  - Trigger execution identifiers are external references only
  - parent/replay lineage stays runtime-owned

- Version handshake contract
  - each executable run must capture immutable agent/config/revision identifiers
  - Trigger payloads should carry revision ids, not mutable config blobs

- Event contract
  - runtime events are operator-facing control-plane facts
  - worker logs remain execution telemetry, not source of truth
  - normalized events should cover command, approval, dispatch, task, artifact, completion, failure, and replay milestones

## Required Local Preconditions

Run all commands from `/home/workspace/Hermes-Central-Command`.

Before Phase 1, make sure these commands work:

```bash
cd /home/workspace/Hermes-Central-Command
uv --version
node --version
npm --version
supabase --version
```

If the local Supabase stack is not running, start it before Phase 2:

```bash
cd /home/workspace/Hermes-Central-Command
supabase start
```

Use this local Postgres URL for repository-layer tests unless the environment is already exporting `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql://postgres:***@127.0.0.1:54322/postgres
```

## Phase 1 — Verify the current baseline before changing code

### Goal

Confirm the repo is in the expected pre-implementation state before adding persistence, Trigger lifecycle callbacks, managed-agent primitives, or UI work.

### Files

No file edits in this phase.

### Steps

1. Re-read these documents before touching code:
   - `README.md`
   - `CONTEXT.md`
   - `CODEX.md`
   - `WAT_Architecture.md`
   - `docs/superpowers/specs/2026-04-13-hermes-mission-control-architecture-design.md`
   - `docs/superpowers/specs/2026-04-13-hermes-mission-control-ui-design.md`
   - `docs/mission-control-wiki/concepts/managed-agent-runtime-patterns.md`
   - `docs/mission-control-wiki/entities/claude-managed-agents.md`
2. Confirm there is no `apps/mission-control/` directory yet.
3. Confirm the current runtime still depends on `app/services/run_service.py` in-memory state.
4. Confirm the current Trigger worker files are only the marketing scaffold:
   - `trigger/src/marketing/runMarketResearch.ts`
   - `trigger/src/marketing/createCampaignBrief.ts`
   - `trigger/src/marketing/draftCampaignAssets.ts`
   - `trigger/src/marketing/assembleLaunchProposal.ts`
5. Run the current automated checks unchanged.

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
uv run pytest -q
npx tsc -p trigger/tsconfig.json --noEmit
```

### Exit Gate

Do not continue until both commands pass and the repo state matches the starting-point assumptions above.

---

## Phase 2 — Replace process-local persistence with a Supabase-backed runtime substrate

### Goal

Create the first persistent control-plane substrate for commands, approvals, runs, run events, and artifacts. This phase only establishes storage and repository access. Do not refactor API behavior yet.

### Files

Modify:
- `pyproject.toml`
- `app/core/config.py`
- `tests/test_package_layout.py`

Create:
- `supabase/migrations/202604130002_mission_control_runtime_persistence.sql`
- `app/db/__init__.py`
- `app/db/client.py`
- `app/db/commands.py`
- `app/db/approvals.py`
- `app/db/runs.py`
- `app/db/events.py`
- `app/db/artifacts.py`
- `tests/conftest.py`
- `tests/db/test_commands_repository.py`
- `tests/db/test_approvals_repository.py`
- `tests/db/test_runs_repository.py`

### Steps

1. Add the database dependency and runtime configuration.
   - Add `psycopg[binary]` to `pyproject.toml`.
   - Add `database_url` to `app/core/config.py`.
   - Keep existing runtime API key settings intact.
2. Create `app/db/client.py` as the only database connection entry point for this phase.
   - Expose a connection factory.
   - Expose a transaction helper.
   - Do not let service modules open ad hoc connections directly.
3. Create repository modules with narrow responsibilities.
   - `app/db/commands.py` handles command insert, dedupe lookup, command fetch by ID, and command status update.
   - `app/db/approvals.py` handles approval insert, fetch by ID, and approval status update.
   - `app/db/runs.py` handles run insert, fetch by ID, child-run creation, and status update.
   - `app/db/events.py` handles append-only run-event writes and event reads by run ID.
   - `app/db/artifacts.py` handles artifact writes and artifact reads by run ID.
4. Create `supabase/migrations/202604130002_mission_control_runtime_persistence.sql`.
   - Extend the existing schema instead of rewriting `202604130001_hermes_control_plane_core.sql`.
   - Add only the missing columns, constraints, and indexes required for repository-backed commands, approvals, runs, run events, and artifacts.
   - Keep tenant scope on `business_id` and `environment`.
   - Preserve command uniqueness on `(business_id, environment, command_type, idempotency_key)`.
   - Preserve append-only event and artifact history.
   - Do not add any scheduler, queue, or canvas tables.
5. Write repository tests before wiring services.
   - `tests/db/test_commands_repository.py` must prove command dedupe works on `(business_id, environment, command_type, idempotency_key)`.
   - `tests/db/test_approvals_repository.py` must prove approval rows round-trip with actor, status, and timestamps.
   - `tests/db/test_runs_repository.py` must prove parent/child run lineage, replay reason persistence, event writes, and artifact writes.
6. Update `tests/test_package_layout.py` so it imports the new `app.db` modules.

### Concrete Test Cases

`tests/db/test_commands_repository.py`
- creating the same command twice returns the same command row
- a different `environment` does not collide with the same idempotency key
- a different `command_type` does not collide with the same idempotency key

`tests/db/test_approvals_repository.py`
- a newly inserted approval defaults to `pending`
- approving a row stores `actor_id` and `approved_at`
- fetching a missing approval returns `None`

`tests/db/test_runs_repository.py`
- creating a run stores `command_id`, `business_id`, `environment`, and `status`
- creating a replay child run stores `parent_run_id` and `replay_reason`
- appending two run events preserves order by `created_at`
- appending an artifact stores `artifact_type` and JSON payload

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
supabase db reset --local
uv run pytest tests/db/test_commands_repository.py tests/db/test_approvals_repository.py tests/db/test_runs_repository.py tests/test_package_layout.py -q
```

### Exit Gate

Do not continue until the migration applies cleanly and all repository tests pass against local Supabase/Postgres.

---

## Phase 3 — Move the command, approval, run, and replay APIs onto the persisted runtime contract

### Goal

Replace the in-memory control-plane behavior with repository-backed behavior while keeping policy decisions in FastAPI services. This phase freezes the deterministic runtime contract before Trigger.dev integration.

### Files

Modify:
- `app/models/commands.py`
- `app/models/approvals.py`
- `app/models/runs.py`
- `app/services/command_service.py`
- `app/services/approval_service.py`
- `app/services/run_service.py`
- `app/services/replay_service.py`
- `app/api/commands.py`
- `app/api/approvals.py`
- `app/api/runs.py`
- `app/api/replays.py`
- `tests/api/test_commands.py`
- `tests/api/test_approvals.py`
- `tests/api/test_runs.py`
- `tests/api/test_replays.py`

### Steps

1. Refactor `app/services/run_service.py` first.
   - Remove the in-memory `STORE` dependency.
   - Replace direct in-memory mutations with repository calls.
   - Keep `create_run`, `get_run`, and `get_run_detail` as the service entry points.
2. Refactor `app/services/command_service.py`.
   - Keep policy classification in this service.
   - Use `app/db/commands.py` for dedupe lookup and command creation.
   - On safe autonomous commands, create a queued run through `run_service`.
   - On approval-required commands, create an approval through `approval_service`.
3. Refactor `app/services/approval_service.py`.
   - Persist approval decisions.
   - Re-approving an already approved request must return the existing run instead of creating a duplicate run.
4. Refactor `app/services/replay_service.py`.
   - Persist the replay-request event on the parent run.
   - Safe autonomous replays must create a child run immediately.
   - Approval-required replays must create a new approval and return `409` with the new `approval_id`.
5. Tighten the response models.
   - `ReplayResponse` must always include `parent_run_id`, `child_run_id`, `requires_approval`, `approval_id`, and `replay_reason`.
   - `RunDetailResponse` must always include `parent_run_id`, `replay_reason`, `events`, and `artifacts`.
6. Keep endpoint ownership unchanged.
   - `app/api/commands.py` remains the typed command-ingestion boundary.
   - `app/api/approvals.py` remains the approval-decision boundary.
   - `app/api/replays.py` remains the replay-decision boundary.
   - Do not move policy logic into Trigger.dev.

### Concrete Test Cases

`tests/api/test_commands.py`
- safe autonomous command returns `201`, `policy=safe_autonomous`, and a non-null `run_id`
- approval-required command returns `201`, `policy=approval_required`, and a non-null `approval_id`
- resubmitting the exact same command returns `200` with `deduped=true`

`tests/api/test_approvals.py`
- approving a pending approval returns a run ID
- approving the same approval twice returns the same run ID
- approving a missing approval returns `404`

`tests/api/test_runs.py`
- `GET /runs/{run_id}` returns a persisted run with `events` and `artifacts`
- a replay-created child run exposes `parent_run_id`

`tests/api/test_replays.py`
- replaying a safe autonomous run returns `201` with `requires_approval=false`
- replaying an approval-required run returns `409` with `requires_approval=true`
- replay responses include `replay_reason`

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py -q
```

### Exit Gate

Do not continue until the runtime API contract is persisted, deterministic, and no code path depends on `app/services/run_service.py` in-memory state.

---

## Phase 4 — Wire Trigger.dev to the frozen runtime lifecycle without duplicating orchestration primitives

### Goal

Move long-running execution and lifecycle reporting into Trigger.dev while keeping Hermes as the control plane and source of truth.

### Files

Modify:
- `trigger/trigger.config.ts`
- `trigger/bootstrap.ts`
- `trigger/src/shared/runtimeApi.ts`
- `trigger/src/marketing/runMarketResearch.ts`
- `trigger/src/marketing/createCampaignBrief.ts`
- `trigger/src/marketing/draftCampaignAssets.ts`
- `trigger/src/marketing/assembleLaunchProposal.ts`
- `app/main.py`
- `tests/api/test_marketing_runtime.py`
- `tests/domains/marketing/test_marketing_flow.py`

Create:
- `trigger/src/runtime/dispatchCommand.ts`
- `trigger/src/runtime/reportRunLifecycle.ts`
- `trigger/src/runtime/queueKeys.ts`
- `app/models/run_events.py`
- `app/api/trigger_callbacks.py`
- `app/services/run_lifecycle_service.py`
- `tests/api/test_trigger_callbacks.py`

### Steps

1. Add a Hermes-owned callback contract for Trigger.dev.
   - `app/api/trigger_callbacks.py` must expose callback endpoints for:
     - run started
     - run completed
     - run failed
     - artifact produced
   - `app/services/run_lifecycle_service.py` must translate those callbacks into persisted run status updates, run-event writes, and artifact writes.
2. Standardize Trigger.dev runtime helpers.
   - `trigger/src/runtime/dispatchCommand.ts` must be the single entry point for dispatching Hermes command work into Trigger tasks.
   - `trigger/src/runtime/reportRunLifecycle.ts` must be the single entry point for reporting lifecycle callbacks back to Hermes.
   - `trigger/src/runtime/queueKeys.ts` must derive tenant-aware queue keys from `businessId` and `environment`.
3. Update `trigger/trigger.config.ts`.
   - Add explicit concurrency settings keyed by business/environment where Trigger.dev supports it.
   - Keep retries enabled in Trigger.dev.
   - Do not add Hermes-side retry loops.
4. Update the four marketing tasks.
   - Each task must accept enough context to report lifecycle state back to Hermes: `runId`, `commandId`, `businessId`, `environment`, and `idempotencyKey`.
   - Each task must report `run_started` before calling the FastAPI marketing endpoint.
   - Each task must report artifact creation after receiving the endpoint response.
   - Each task must report `run_completed` or `run_failed` exactly once.
5. Use Trigger.dev primitives directly.
   - Use Trigger queues for concurrency control.
   - Use Trigger retries for retry behavior.
   - Use Trigger task chaining for the marketing workflow.
   - Do not add a Hermes-native scheduler table, retry counter, or orchestration canvas.
6. Register the new callback router in `app/main.py`.

### Concrete Test Cases

`tests/api/test_trigger_callbacks.py`
- posting `run_started` updates a run from `queued` to `in_progress`
- posting `artifact_produced` appends an artifact row without mutating prior artifacts
- posting `run_completed` sets the run status to `completed`
- posting `run_failed` sets the run status to `failed` and stores the error payload

`tests/api/test_marketing_runtime.py`
- the marketing endpoints still return the expected artifact types
- the runtime callback payloads match the TypeScript worker contract exactly

`tests/domains/marketing/test_marketing_flow.py`
- the marketing command still maps to the same ordered task chain
- the Trigger-side dispatch helper does not duplicate steps

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
npx tsc -p trigger/tsconfig.json --noEmit
uv run pytest tests/api/test_trigger_callbacks.py tests/api/test_marketing_runtime.py tests/domains/marketing/test_marketing_flow.py -q
```

### Exit Gate

Do not continue until Trigger.dev is the only durable execution layer and Hermes is still the only canonical state layer.

---

## Phase 5 — Add managed-agent primitives: versioned agents, isolated sessions, permissions, outcomes, and connect-later assets

### Goal

Implement the Claude-style managed-agent control-plane primitives and the GoHighLevel-inspired draft/production plus connect-later ergonomics, without adding page-builder features.

### Files

Modify:
- `app/services/hermes_tools_service.py`
- `app/api/hermes_tools.py`
- `app/main.py`
- `tests/api/test_hermes_tools.py`
- `tests/test_package_layout.py`

Create:
- `supabase/migrations/202604130003_mission_control_managed_agents.sql`
- `app/db/agents.py`
- `app/db/sessions.py`
- `app/db/permissions.py`
- `app/db/outcomes.py`
- `app/models/agents.py`
- `app/models/sessions.py`
- `app/models/permissions.py`
- `app/models/outcomes.py`
- `app/models/agent_assets.py`
- `app/services/agent_registry_service.py`
- `app/services/session_service.py`
- `app/services/permission_service.py`
- `app/services/outcome_service.py`
- `app/services/agent_asset_service.py`
- `app/api/agents.py`
- `app/api/sessions.py`
- `app/api/outcomes.py`
- `app/api/agent_assets.py`
- `tests/api/test_agents.py`
- `tests/api/test_sessions.py`
- `tests/api/test_outcomes.py`
- `tests/api/test_agent_assets.py`

### Steps

1. Create the managed-agent schema migration in `supabase/migrations/202604130003_mission_control_managed_agents.sql`.
   - Add tables for agent definitions, agent revisions, sessions, permission policies, outcomes, rubrics, and agent assets.
   - Keep agent definitions separate from sessions.
   - Keep outcomes separate from run events.
   - Keep asset bindings separate from agent definitions.
2. Implement versioned agents.
   - `app/models/agents.py` must represent a stable `agent_id` plus immutable revisions.
   - Support revision states `draft`, `published`, and `archived`.
   - Support a published revision that production sessions can reference.
   - Support clone ergonomics by creating a new draft revision from an existing published revision.
3. Implement isolated sessions.
   - `app/models/sessions.py` and `app/services/session_service.py` must create session records that reference an agent revision, not mutable prompt text.
   - Sessions must have isolated thread state and their own status timeline.
4. Implement permission policies.
   - `app/models/permissions.py` and `app/services/permission_service.py` must support `always_allow`, `always_ask`, and `forbidden`.
   - Hermes tools must check permission state before execution.
5. Implement outcome and rubric evaluation.
   - `app/models/outcomes.py` and `app/services/outcome_service.py` must store explicit outcome targets, rubric definitions, evaluator results, and pass/fail status.
   - This is the place to implement the Claude-style outcome loop; do not move it into Trigger.dev.
6. Implement connect-later asset behavior.
   - `app/models/agent_assets.py` and `app/services/agent_asset_service.py` must support operational assets that can be created before they are bound.
   - Limit asset scope to operational bindings such as calendars, forms, phone numbers, inboxes, or webhook-backed assets.
   - Explicitly exclude landing pages and page-builder artifacts.
7. Expose new API surfaces.
   - `app/api/agents.py`
   - `app/api/sessions.py`
   - `app/api/outcomes.py`
   - `app/api/agent_assets.py`
8. Register the new routers in `app/main.py` and update Hermes tool listing so the runtime can expose agent-aware tools without bypassing permission checks.

### Concrete Test Cases

`tests/api/test_agents.py`
- creating an agent creates a stable `agent_id` and an initial `draft` revision
- publishing a draft revision marks it as the active production revision
- cloning a published revision creates a new draft revision with copied config
- archived revisions remain queryable but cannot be published again

`tests/api/test_sessions.py`
- creating two sessions from the same revision produces isolated session IDs and thread timelines
- a session cannot be created from an archived revision
- a session still points to the original revision after a newer revision is published

`tests/api/test_outcomes.py`
- evaluating an outcome stores rubric criteria and evaluator result
- a failed rubric stores failure details without mutating the original artifact
- a passed rubric marks the outcome as satisfied

`tests/api/test_agent_assets.py`
- creating an unbound asset stores `connect_later=true`
- binding a connect-later asset updates only the asset record, not the agent revision
- asset types outside operational scope are rejected

`tests/api/test_hermes_tools.py`
- a tool with `always_ask` permission returns an approval path instead of direct execution
- a tool with `forbidden` permission is rejected

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
supabase db reset --local
uv run pytest tests/api/test_agents.py tests/api/test_sessions.py tests/api/test_outcomes.py tests/api/test_agent_assets.py tests/api/test_hermes_tools.py tests/test_package_layout.py -q
```

### Exit Gate

Do not continue until agent versioning, session isolation, permissions, outcomes, and connect-later assets all work without introducing page-builder scope or duplicate orchestration behavior.

---

## Phase 6 — Add Mission Control read models and the native React UI shell

### Goal

Expose backend read models for Mission Control and build the first native operator cockpit inside this repo.

### Files

Modify:
- `package.json`
- `app/main.py`

Create:
- `app/models/mission_control.py`
- `app/services/mission_control_service.py`
- `app/api/mission_control.py`
- `tests/api/test_mission_control.py`
- `apps/mission-control/package.json`
- `apps/mission-control/tsconfig.json`
- `apps/mission-control/index.html`
- `apps/mission-control/vite.config.ts`
- `apps/mission-control/vitest.config.ts`
- `apps/mission-control/src/main.tsx`
- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/styles.css`
- `apps/mission-control/src/lib/api.ts`
- `apps/mission-control/src/lib/queryClient.ts`
- `apps/mission-control/src/pages/DashboardPage.tsx`
- `apps/mission-control/src/pages/InboxPage.tsx`
- `apps/mission-control/src/pages/ApprovalsPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`
- `apps/mission-control/src/pages/AgentsPage.tsx`
- `apps/mission-control/src/pages/SettingsPage.tsx`
- `apps/mission-control/src/components/MissionControlShell.tsx`
- `apps/mission-control/src/components/DashboardSummary.tsx`
- `apps/mission-control/src/components/InboxList.tsx`
- `apps/mission-control/src/components/ConversationThread.tsx`
- `apps/mission-control/src/components/ContextPanel.tsx`
- `apps/mission-control/src/components/ApprovalQueue.tsx`
- `apps/mission-control/src/components/RunTimeline.tsx`
- `apps/mission-control/src/components/AgentRegistryTable.tsx`
- `apps/mission-control/src/components/ConnectLaterPanel.tsx`
- `apps/mission-control/src/test/setup.ts`
- `apps/mission-control/src/components/MissionControlShell.test.tsx`
- `apps/mission-control/src/pages/DashboardPage.test.tsx`

### Steps

1. Add backend read models first.
   - `app/models/mission_control.py` must define the response shapes for:
     - dashboard summary
     - inbox list and selected thread
     - approvals queue
     - runs list with status and lineage
     - agent registry summary
     - connect-later asset summary
   - `app/services/mission_control_service.py` must assemble these read models from persisted tables.
   - `app/api/mission_control.py` must expose these routes:
     - `GET /mission-control/dashboard`
     - `GET /mission-control/inbox`
     - `GET /mission-control/approvals`
     - `GET /mission-control/runs`
     - `GET /mission-control/agents`
     - `GET /mission-control/settings/assets`
2. Register the new Mission Control router in `app/main.py`.
3. Add root package scripts in `package.json` for the UI.
   - `mission-control:dev`
   - `mission-control:test`
   - `mission-control:build`
4. Build the React app manually in `apps/mission-control/`.
   - Keep the shell native to this repo.
   - Keep the UI dense and operational.
   - Keep all writes flowing back through Hermes APIs.
5. Build the initial screen set.
   - `DashboardPage.tsx` for system status, approvals, active runs, failed runs, and agent health.
   - `InboxPage.tsx` with `InboxList.tsx`, `ConversationThread.tsx`, and `ContextPanel.tsx`.
   - `ApprovalsPage.tsx` with `ApprovalQueue.tsx`.
   - `RunsPage.tsx` with `RunTimeline.tsx`.
   - `AgentsPage.tsx` with `AgentRegistryTable.tsx`.
   - `SettingsPage.tsx` with `ConnectLaterPanel.tsx` for operational asset binding only.
6. Do not add any page-builder, landing-page, or visual funnel editor screens.

### Concrete Test Cases

`tests/api/test_mission_control.py`
- dashboard endpoint returns approval count, active run count, failed run count, and active agent count
- inbox endpoint returns conversation summaries plus a selected thread payload
- runs endpoint returns run lineage including `parent_run_id`
- agents endpoint returns revision state and active production revision
- settings/assets endpoint returns connect-later asset status

`apps/mission-control/src/components/MissionControlShell.test.tsx`
- shell renders the left navigation and active workspace

`apps/mission-control/src/pages/DashboardPage.test.tsx`
- dashboard renders counts from the backend response without embedding business logic in the component

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
npm --prefix apps/mission-control install
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
uv run pytest tests/api/test_mission_control.py -q
```

### Exit Gate

Do not continue until the UI is native, backend-driven, and visibly centered on inbox, approvals, runs, agents, and operational asset binding.

---

## Phase 7 — Final documentation sync and release gate

### Goal

Bring the docs up to date after implementation and run the final verification suite.

### Files

Modify:
- `README.md`
- `CONTEXT.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-13-hermes-mission-control-architecture-design.md`
- `docs/superpowers/specs/2026-04-13-hermes-mission-control-ui-design.md`
- `docs/mission-control-wiki/index.md`
- `docs/mission-control-wiki/concepts/agentic-first-command-center.md`
- `docs/mission-control-wiki/concepts/managed-agent-runtime-patterns.md`
- `docs/mission-control-wiki/concepts/mission-control-ui.md`
- `docs/mission-control-wiki/entities/claude-managed-agents.md`
- `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`

### Steps

1. Update operator-facing docs to reflect the implemented architecture.
2. Keep all docs aligned on the same boundaries:
   - Hermes is the control plane.
   - Supabase/Postgres is the canonical state layer.
   - Trigger.dev is the durable execution layer.
   - Claude Managed Agents contributes versioning, sessions, permissions, events, and outcomes.
   - GoHighLevel contributes only draft/production, clone ergonomics, and connect-later operational assets.
   - Page builders and landing pages remain out of scope.
3. Update `CONTEXT.md` and `memory.md` with the completed implementation status and latest change-log entry.
4. Re-read this plan and remove any statements that no longer match the implemented code.

### Commands

```bash
cd /home/workspace/Hermes-Central-Command
supabase db reset --local
uv run pytest -q
npx tsc -p trigger/tsconfig.json --noEmit
npm --prefix apps/mission-control run build
git diff --check
```

### Exit Gate

Stop only when every command above passes and the docs describe the shipped architecture without contradiction.

---

## Self-Review Checklist

Use this checklist before handing the work back:

- [ ] Every phase was executed in order without skipping an exit gate.
- [ ] No phase introduced a Hermes-native scheduler, retry engine, queueing system, or orchestration canvas.
- [ ] Trigger.dev is the only durable execution engine in the final design.
- [ ] Supabase/Postgres remains the canonical state layer for commands, approvals, runs, events, artifacts, agents, sessions, outcomes, and assets.
- [ ] Policy decisions still live in FastAPI services, not in the frontend and not in Trigger.dev.
- [ ] Agent definitions are versioned and separate from sessions.
- [ ] Session state is isolated per session/thread.
- [ ] Tool permissions are explicit: `always_allow`, `always_ask`, or `forbidden`.
- [ ] Outcome and rubric evaluation exists as a Hermes-native control-plane primitive.
- [ ] Draft/production and clone ergonomics exist for agent revisions.
- [ ] Connect-later behavior exists only for operational assets.
- [ ] No landing-page, page-builder, or website-composer features were added.
- [ ] Every section in this plan lists exact files and concrete verification commands.
- [ ] `CONTEXT.md` and `memory.md` were updated at the end.
- [ ] Final docs use the current wiki path structure under `docs/mission-control-wiki/concepts` and `docs/mission-control-wiki/entities`.
