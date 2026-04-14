# Mission Control Finish Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish `feature/mission-control-ai-first` into a coherent, live-backed Mission Control scaffold without risking the current Supabase project.

**Architecture:** Split the work into two tracks. Track A finishes the branch safely with no Supabase schema changes by aligning backend read models and frontend contracts. Track B is a separate, gated persistence rollout that lands only after Track A is green and only through additive migrations plus isolated verification.

**Tech Stack:** FastAPI, Pydantic, pytest, React, TypeScript, Vite, Vitest, Supabase CLI, Postgres migrations.

---

## Chunk 1: Safe Branch Completion Without Schema Changes

### Task 1: Freeze the Mission Control contract

**Files:**
- Modify: `app/api/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/models/mission_control.py`
- Modify: `apps/mission-control/src/lib/api.ts`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/pages/DashboardPage.tsx`
- Modify: `apps/mission-control/src/pages/InboxPage.tsx`
- Test: `tests/api/test_mission_control.py`
- Test: `apps/mission-control/src/pages/DashboardPage.test.tsx`
- Test: `apps/mission-control/src/components/MissionControlShell.test.tsx`

- [ ] Write failing API tests for the missing read surfaces the UI expects: approvals, agents, and settings/assets.
- [ ] Write failing API tests for the full dashboard and inbox payload shape that the frontend actually consumes.
- [ ] Decide one contract owner.
For this branch, make FastAPI the owner of the Mission Control read model and keep the frontend thin.
- [ ] Extend `/mission-control/*` so the backend exposes all read surfaces needed by the shell:
  - `/mission-control/dashboard`
  - `/mission-control/inbox`
  - `/mission-control/approvals`
  - `/mission-control/runs`
  - `/mission-control/agents`
  - `/mission-control/settings/assets`
- [ ] Keep the implementation additive.
Do not rewrite the existing `agents`, `permissions`, `sessions`, `outcomes`, or `agent-assets` domain routes just to serve the UI.
- [ ] Update the frontend API client to consume the backend-owned read model instead of assuming fixture-only camelCase shapes.
- [ ] Keep fixtures only as explicit local fallback or demo data, not as a silent substitute for missing production routes.
- [ ] Run:
`uv run pytest tests/api/test_mission_control.py -q`
- [ ] Run:
`npm --prefix apps/mission-control run test -- --run`
- [ ] Run:
`npm --prefix apps/mission-control run typecheck`
- [ ] Run:
`npm --prefix apps/mission-control run build`

### Task 2: Add list/read helpers behind existing in-memory repositories

**Files:**
- Modify: `app/db/agents.py`
- Modify: `app/db/approvals.py`
- Modify: `app/db/agent_assets.py`
- Modify: `app/services/agent_registry_service.py`
- Modify: `app/services/approval_service.py`
- Modify: `app/services/agent_asset_service.py`
- Test: `tests/api/test_agents.py`
- Test: `tests/api/test_agent_assets.py`

- [ ] Write failing tests for list-style reads needed by Mission Control.
- [ ] Add repository helpers for:
  - listing agents
  - listing pending approvals
  - listing agent assets
- [ ] Keep these reads tenant-aware using the same `business_id` and `environment` filters already used in Mission Control.
- [ ] Do not add persistence-specific assumptions here.
These helpers must work for the current in-memory adapter and later Supabase adapter.
- [ ] Re-run the focused test files, then the full Python suite:
`uv run pytest -q`

### Task 3: Sync docs to the actual branch state

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`

- [ ] Update the runtime surface section so it distinguishes:
  - live domain routes
  - live Mission Control read routes
  - scaffold-only persistence seams
- [ ] Record that the branch is finished as a live read-model scaffold, not a Supabase-backed control plane.
- [ ] Keep `CONTEXT.md` short and point to `memory.md` for deeper notes.

## Chunk 2: Separate Supabase Persistence Rollout

### Task 4: Land runtime persistence as additive migrations only

**Files:**
- Create: `supabase/migrations/202604130002_mission_control_runtime_persistence.sql`
- Modify: `supabase/migrations/202604130003_mission_control_managed_agents.sql`
- Modify: `app/db/client.py`
- Modify: `app/core/config.py`
- Test: `tests/db/test_commands_repository.py`
- Test: `tests/db/test_approvals_repository.py`
- Test: `tests/db/test_runs_repository.py`

- [ ] Do not edit `202604130001_hermes_control_plane_core.sql`.
Treat it as the stable baseline.
- [ ] Make `202604130002_mission_control_runtime_persistence.sql` additive only.
Use `create table if not exists`, `alter table ... add column if not exists`, new indexes, and new policies where needed.
- [ ] Replace the placeholder `202604130003_mission_control_managed_agents.sql` with additive managed-agent tables only after the runtime persistence layer is proven locally.
- [ ] Keep all new tables tenant-scoped with `business_id` and `environment`.
- [ ] Keep events and site events append-only.
- [ ] Preserve command idempotency uniqueness.
- [ ] Preserve parent/child run lineage and replay fields.
- [ ] Use local Supabase first:
`supabase db reset --local`
- [ ] Run focused repository tests against local Postgres before touching any remote project.

### Task 5: Switch services to repositories behind a gated backend flag

**Files:**
- Modify: `app/services/command_service.py`
- Modify: `app/services/approval_service.py`
- Modify: `app/services/run_service.py`
- Modify: `app/services/replay_service.py`
- Modify: `app/services/run_lifecycle_service.py`
- Modify: `tests/api/test_commands.py`
- Modify: `tests/api/test_approvals.py`
- Modify: `tests/api/test_runs.py`
- Modify: `tests/api/test_replays.py`
- Modify: `tests/api/test_trigger_callbacks.py`

- [ ] Keep `control_plane_backend=memory` as the default until local Supabase-backed tests pass.
- [ ] Add failing tests that run against both adapters where practical.
- [ ] Move writes to repository-backed flows one service at a time.
- [ ] After each service migration, run the focused tests and then the full suite.
- [ ] Only enable `control_plane_backend=supabase` in a non-production environment first.

### Task 6: Remote rollout with a no-surprises gate

**Files:**
- Modify: `README.md`
- Modify: `memory.md`

- [ ] Before any remote migration, pull current remote schema if dashboard drift exists:
`supabase db pull`
- [ ] Apply to a preview branch or staging project first, not production.
- [ ] Verify:
  - migrations apply cleanly
  - API tests pass
  - Mission Control shell loads live data
  - existing command/approval/run flows still work
- [ ] Promote to production only after staging verification and a fresh backup window.

## Rollout Order

- [ ] Finish Chunk 1 first.
- [ ] Treat Chunk 2 as a separate branch or at minimum a separate commit series.
- [ ] Do not combine UI contract fixes and Supabase persistence cutover in one deploy.

## Risk Notes

- [ ] The branch can be finished convincingly without changing Supabase today.
- [ ] Schema work is required only if we want real persistence instead of the current in-memory adapter.
- [ ] The least risky schema path is additive migrations plus local reset plus preview/staging verification before any production push.
