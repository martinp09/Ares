# Mission Control Supabase Persistence Rollout Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current in-memory Mission Control runtime state with Supabase-backed persistence in a separate branch, without changing the finished Mission Control contract branch and without taking schema or rollout risks.

**Architecture:** Treat persistence as a second track after the Mission Control contract is frozen. Keep the existing FastAPI service and repository boundaries, add only additive Supabase migrations, cut over by adapter behind `control_plane_backend`, and promote through local reset, preview or staging, then production. Mission Control read models stay runtime-owned and derive from canonical tables rather than becoming a second write path.

**Tech Stack:** FastAPI, Pydantic, pytest, Supabase CLI, Postgres, React, TypeScript, Vitest.

---

**Status:** Design-only. Do not implement this plan on the finished Mission Control contract branch.

**Recommended branch:** `feature/mission-control-supabase-persistence`

**Hard rollout rules**

- [ ] Start this work only after the Mission Control contract branch is green and documentation-synced.
- [ ] Do not mix Mission Control contract fixes and persistence changes in one branch, one PR, or one deploy.
- [ ] Do not edit `supabase/migrations/202604130001_hermes_control_plane_core.sql`.
- [ ] Keep every schema change additive only: new tables, new indexes, new policies, or `alter table ... add column if not exists`.
- [ ] Run `supabase db reset --local` before any remote migration or backend cutover decision.
- [ ] Promote to preview or staging before production.
- [ ] Do not switch production traffic to `control_plane_backend=supabase` until non-production verification is green.

## Current In-Memory Surface To Replace

- `commands` in `app/db/client.py` -> `public.commands`
- `approvals` in `app/db/client.py` -> `public.approvals`
- `runs` in `app/db/client.py` -> `public.runs`
- run-scoped `events` currently embedded on `RunRecord.events` -> `public.events`
- run-scoped `artifacts` currently embedded on `RunRecord.artifacts` -> `public.artifacts`
- `agents` in `app/db/client.py` -> future `public.agents`
- `agent_revisions` and `agent_revision_ids_by_agent` -> future `public.agent_revisions`
- `sessions` -> future `public.agent_sessions` plus a timeline or event table
- `permissions` and `permission_keys` -> future `public.agent_tool_permissions`
- `outcomes` -> future `public.outcome_evaluations` and any rubric-support tables needed
- `agent_assets` -> future `public.agent_operational_assets`
- `mission_control_threads` -> runtime-owned Mission Control read models derived from canonical tables plus `contacts`, `conversations`, and `site_events`

## Design Decisions To Freeze Before Implementation

- [ ] Keep FastAPI as the policy boundary and Supabase as the canonical state layer.
- [ ] Keep repository modules in `app/db/` as the only persistence adapters. Services should not open SQL connections directly.
- [ ] Preserve tenant scope on every durable record with `business_id` and `environment`.
- [ ] Keep command dedupe runtime-owned on `(business_id, environment, command_type, idempotency_key)`.
- [ ] Keep events append-only and artifacts immutable after write.
- [ ] Keep replay lineage runtime-owned through `parent_run_id`, `replay_source_run_id`, and `replay_reason`.
- [ ] Keep Mission Control read models backend-owned. The UI consumes them; it does not rebuild them client-side.
- [ ] Prefer derived read models over duplicate write paths. If a projection table is needed for Mission Control latency, it must be rebuildable from canonical runtime facts.

## Phase 0: Branch Separation And Baseline Audit

**Purpose:** Freeze what is allowed to change on the persistence branch and confirm the contract branch remains untouched.

**Planned files later**

- `docs/superpowers/plans/2026-04-13-mission-control-finish-plan.md`
- `docs/superpowers/plans/2026-04-13-mission-control-supabase-persistence-plan.md`
- `CONTEXT.md`
- `memory.md`

**Implementation steps later**

- [ ] Branch from the finished Mission Control contract commit into `feature/mission-control-supabase-persistence`.
- [ ] Tag or otherwise note the contract-only deploy candidate before persistence work starts.
- [ ] Confirm the branch still defaults to `control_plane_backend=memory`.
- [ ] Confirm there are no pending frontend contract fixes, no pending Mission Control route additions, and no schema edits mixed into the starting commit.

**Exit gate**

- [ ] Persistence work is isolated to its own branch and the contract branch remains releasable without Supabase cutover.

## Phase 1: Schema Compatibility And Runtime Core Design

**Purpose:** Reconcile the current Python runtime contracts with the existing SQL baseline before any service cutover.

**Planned files later**

- `supabase/migrations/202604130002_mission_control_runtime_persistence.sql`
- `app/models/commands.py`
- `app/models/approvals.py`
- `app/models/runs.py`
- `app/db/client.py`
- `app/db/commands.py`
- `app/db/approvals.py`
- `app/db/runs.py`
- `app/db/events.py`
- `app/db/artifacts.py`
- `tests/db/test_commands_repository.py`
- `tests/db/test_approvals_repository.py`
- `tests/db/test_runs_repository.py`

**Design scope**

- [ ] Map the current string runtime IDs (`cmd_*`, `apr_*`, `run_*`) to database storage without breaking API contracts.
- [ ] Decide whether the canonical database ID exposed to Python remains a text primary key, or whether bigint surrogate keys stay internal while text runtime IDs become unique business keys.
- [ ] Reconcile enum mismatches before coding:
  - `CommandStatus` currently uses `accepted` and `awaiting_approval`, while SQL uses `queued` and `approval_required`.
  - `RunStatus` currently uses `in_progress`, while SQL uses `running`.
  - approvals track `approved_at` in Python but `decided_at` in SQL.
- [ ] Normalize the current embedded run events and artifacts into `public.events` and `public.artifacts` without changing the API response shape.
- [ ] Keep `202604130002_mission_control_runtime_persistence.sql` additive only and targeted at runtime core tables, indexes, and policies.
- [ ] Do not repurpose `202604130003_mission_control_managed_agents.sql` during this phase.

**Test gate**

- [ ] Repository tests prove command dedupe, approval transitions, run lineage, append-only event writes, and artifact reads against local Supabase/Postgres.
- [ ] `supabase db reset --local` applies `202604130001` plus the new additive runtime migration cleanly.

**Exit gate**

- [ ] The runtime core schema design is internally consistent and can store commands, approvals, runs, events, and artifacts without changing API contracts.

## Phase 2: Repository And Service Cutover For Commands, Approvals, Runs, Events, And Artifacts

**Purpose:** Move the runtime core from process-local state to repository-backed state behind the existing backend toggle.

**Planned files later**

- `app/db/client.py`
- `app/services/command_service.py`
- `app/services/approval_service.py`
- `app/services/run_service.py`
- `app/services/replay_service.py`
- `app/services/run_lifecycle_service.py`
- `app/api/commands.py`
- `app/api/approvals.py`
- `app/api/runs.py`
- `app/api/replays.py`
- `app/api/trigger_callbacks.py`
- `tests/api/test_commands.py`
- `tests/api/test_approvals.py`
- `tests/api/test_runs.py`
- `tests/api/test_replays.py`
- `tests/api/test_trigger_callbacks.py`

**Design scope**

- [ ] Keep `control_plane_backend=memory` as the default until the Supabase adapter passes local repository and API tests.
- [ ] Make `app/db/client.py` the only adapter switch point. No service should branch on SQL details.
- [ ] Cut over writes in this order: commands -> approvals -> runs -> events/artifacts -> replay lineage -> Trigger lifecycle callbacks.
- [ ] Preserve idempotent approval behavior so re-approving does not create duplicate runs.
- [ ] Preserve replay behavior so safe replays create child runs and approval-required replays create new approvals.
- [ ] Keep runtime events as normalized records and continue to hydrate `RunDetailResponse.events` from those records.
- [ ] Keep artifact payloads immutable and continue to hydrate `RunDetailResponse.artifacts` from `public.artifacts`.

**Test gate**

- [ ] `uv run pytest tests/db/test_commands_repository.py tests/db/test_approvals_repository.py tests/db/test_runs_repository.py -q`
- [ ] `uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py -q`
- [ ] A local manual check confirms the API still returns the same command, approval, run, replay, event, and artifact payload shapes under both adapters.

**Exit gate**

- [ ] No command, approval, run, event, or artifact path depends on `InMemoryControlPlaneStore`.
- [ ] Switching `control_plane_backend` between `memory` and `supabase` changes storage only, not API behavior.

## Phase 3: Managed-Agent Persistence Design

**Purpose:** Add durable storage for agents, revisions, sessions, permissions, outcomes, and operational assets only after the runtime core is proven.

**Planned files later**

- `supabase/migrations/202604130003_mission_control_managed_agents.sql`
- `app/db/agents.py`
- `app/db/sessions.py`
- `app/db/permissions.py`
- `app/db/outcomes.py`
- `app/db/agent_assets.py`
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
- `tests/api/test_agents.py`
- `tests/api/test_sessions.py`
- `tests/api/test_outcomes.py`
- `tests/api/test_agent_assets.py`
- `tests/api/test_hermes_tools.py`

**Design scope**

- [ ] Keep `agents` separate from immutable `agent_revisions`.
- [ ] Keep `agent_sessions` separate from revision rows and store session timelines append-only.
- [ ] Keep permissions keyed by `(agent_revision_id, tool_name)` with the current `always_allow`, `always_ask`, and `forbidden` modes.
- [ ] Keep outcomes separate from run events; outcomes are evaluation facts, not transport telemetry.
- [ ] Keep operational assets separate from revisions and preserve connect-later semantics.
- [ ] Land the managed-agent migration only after Phase 2 is green locally.
- [ ] Keep `202604130003_mission_control_managed_agents.sql` additive only. If extra read-model support is needed later, create a new migration after `202604130003` instead of back-editing it.

**Test gate**

- [ ] `supabase db reset --local`
- [ ] `uv run pytest tests/api/test_agents.py tests/api/test_sessions.py tests/api/test_outcomes.py tests/api/test_agent_assets.py tests/api/test_hermes_tools.py -q`
- [ ] Existing runtime core tests remain green under `control_plane_backend=supabase`.

**Exit gate**

- [ ] Agents, revisions, sessions, permissions, outcomes, and assets are durable without changing Hermes tool permissions, revision semantics, or connect-later behavior.

## Phase 4: Mission Control Read Models And Projection Strategy

**Purpose:** Replace the current in-memory Mission Control thread and dashboard projections with durable backend-owned read models.

**Planned files later**

- `app/services/mission_control_service.py`
- `app/models/mission_control.py`
- `app/api/mission_control.py`
- `tests/api/test_mission_control.py`
- `apps/mission-control/src/lib/api.ts`
- `apps/mission-control/src/pages/DashboardPage.tsx`
- `apps/mission-control/src/pages/InboxPage.tsx`
- `apps/mission-control/src/pages/ApprovalsPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`
- `apps/mission-control/src/pages/AgentsPage.tsx`
- `apps/mission-control/src/pages/SettingsPage.tsx`

**Design scope**

- [ ] Keep the dashboard and approvals pages sourced from canonical commands, approvals, runs, agents, and assets.
- [ ] Replace `mission_control_threads` in memory with one of two approved paths:
  - derive inbox threads directly from canonical runtime and conversation tables, or
  - persist a rebuildable projection table or view dedicated to Mission Control inbox reads.
- [ ] Prefer Postgres views or projection tables rebuilt from canonical facts over storing operator-only thread state as a second source of truth.
- [ ] Keep `/mission-control/dashboard`, `/mission-control/inbox`, `/mission-control/approvals`, `/mission-control/runs`, `/mission-control/agents`, and `/mission-control/settings/assets` stable at the API boundary.
- [ ] Do not couple the frontend to Supabase directly. The frontend stays on the FastAPI read-model contract.

**Test gate**

- [ ] `uv run pytest tests/api/test_mission_control.py -q`
- [ ] `npm --prefix apps/mission-control run test -- --run`
- [ ] `npm --prefix apps/mission-control run typecheck`
- [ ] `npm --prefix apps/mission-control run build`
- [ ] Manual preview check confirms the Mission Control shell shows live approvals, runs, agents, assets, and inbox data with Supabase-backed state.

**Exit gate**

- [ ] Mission Control reads are durable and backend-owned, with no dependency on `mission_control_threads` inside `InMemoryControlPlaneStore`.

## Phase 5: Preview Or Staging Rollout

**Purpose:** Validate migrations and runtime behavior against a non-production remote Supabase target.

**Planned files later**

- `README.md`
- `CONTEXT.md`
- `memory.md`
- deployment or environment docs as needed

**Design scope**

- [ ] Pull or inspect remote schema first if there is any dashboard drift before applying migrations.
- [ ] Apply additive migrations to preview or staging only.
- [ ] Keep the backend toggle on `memory` until the schema is present and verification data is loaded.
- [ ] Switch the preview or staging environment to `control_plane_backend=supabase` only after migrations and tests pass.
- [ ] Verify read and write flows end to end:
  - command submission
  - approval creation and approval decision
  - run creation and replay lineage
  - Trigger callback updates
  - agent publish or clone flow
  - session event append
  - outcome write
  - asset bind
  - Mission Control dashboard, inbox, approvals, runs, agents, and settings assets

**Test gate**

- [ ] Local reset and full local suite are green before any remote step.
- [ ] Preview or staging smoke tests are green after migrations.
- [ ] Mission Control UI loads live data in preview or staging without fixture fallback hiding failures.

**Exit gate**

- [ ] Preview or staging proves the Supabase backend is safe enough for production review.

## Phase 6: Production Promotion

**Purpose:** Promote the already-verified Supabase persistence path without mixing new contract changes.

**Design scope**

- [ ] Schedule promotion in a clean window with a fresh backup or rollback point.
- [ ] Promote the already-tested migration chain with no extra schema edits.
- [ ] Roll out backend configuration separately from any UI or contract change.
- [ ] Watch runtime writes, approval transitions, replay creation, Trigger callbacks, and Mission Control read surfaces immediately after cutover.
- [ ] Keep the memory adapter available as an emergency rollback path until production is stable.

**Test gate**

- [ ] Production deploy uses the exact migration chain and app build already proven in preview or staging.
- [ ] Post-cutover smoke checks pass for commands, approvals, runs, replays, agents, sessions, outcomes, assets, and Mission Control reads.

**Exit gate**

- [ ] Supabase is the active backend in production and the runtime remains behaviorally identical to the contract branch from the API consumer perspective.

## Schema-Risk Notes

- [ ] **ID strategy risk:** `202604130001` uses bigint primary keys while current Python models emit string IDs with stable prefixes. Choose the storage strategy before writing repositories or API-preserving cutover logic.
- [ ] **Enum drift risk:** current Python status enums and timestamp field names do not line up with the SQL baseline. Resolve naming centrally instead of adding per-service translations ad hoc.
- [ ] **Embedded-to-normalized risk:** events and artifacts are embedded on `RunRecord` today but need normalized storage. The adapter must rehydrate the existing API shape without changing client contracts.
- [ ] **Mission Control projection risk:** `mission_control_threads` is currently a local projection store, while the SQL baseline already has `contacts`, `conversations`, and `site_events`. Avoid introducing a second durable inbox source unless it is explicitly rebuildable.
- [ ] **Migration ordering risk:** runtime core persistence must land before managed-agent persistence. Do not activate or edit `202604130003_mission_control_managed_agents.sql` before `202604130002` is proven locally.
- [ ] **Toggle risk:** partial cutovers are dangerous. Do not run mixed adapters for writes inside one environment; switch at the client boundary only when the full phase is verified.

## Rollout Summary

- [ ] Branch from the finished contract branch into `feature/mission-control-supabase-persistence`.
- [ ] Reconcile schema and model compatibility first.
- [ ] Persist runtime core next.
- [ ] Persist managed-agent primitives after runtime core is stable.
- [ ] Move Mission Control read models onto durable backend-owned projections last.
- [ ] Validate locally, then preview or staging, then production.
