# Mission Control + Enterprise Backlog Master Plan

> This document supersedes and merges `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md` and `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md` as the canonical execution plan for this branch.
>
> Execution root: `/root/.config/superpowers/worktrees/Hermes-Central-Command/mission-control-enterprise-backlog`
>
> Scope rule: build on the current `main` baseline; do not re-do already landed Ares CRM / lead-machine work. Preserve the existing Supabase wiring and extend it additively.

## Goal

Turn the current Ares runtime + Mission Control baseline into the next live enterprise backlog branch by combining:
- Mission Control control-plane hardening
- enterprise agent-platform foundations
- org / actor / release / governance backlog

The product model stays explicit:
- agents are the product unit
- Mission Control is the operator cockpit
- skills are reusable procedures
- host runtimes are adapters
- Trigger.dev is current infrastructure, not the permanent product contract

## Current completion snapshot

| Area | Status | Notes |
|---|---|---|
| Ares CRM runtime phases 0-5 | done | `/ares/run`, `/ares/plans`, `/ares/execution/run`, `/ares/operator/run` merged to `main` |
| Mission Control shell and read models | partial | dashboard/inbox/runs/tasks/lead-machine/operator views exist, but enterprise productization is incomplete |
| Shared control-plane Supabase wiring | partial | core command/run lifecycle and hydrated runtime store seams exist; must be preserved and extended, not replaced |
| Managed-agent / registry / sessions / permissions scaffolding | partial | baseline exists, but org tenancy, release lifecycle, richer host-adapter model, and marketplace path remain open |
| Enterprise backlog plan state | wrong in docs | the 2026-04-15 enterprise plan was mistakenly marked deprecated and must be re-activated as a live source plan |

## Source inputs

Primary source inputs for this branch:
- `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- `docs/hermes-ares-integration-runbook.md`
- current runtime/router files: `CONTEXT.md`, `TODO.md`, `memory.md`

## Non-negotiable rules

1. Preserve existing Supabase wiring.
   - additive extensions only
   - no rollback to memory-only shortcuts on shared control-plane paths
   - no fake fail-fast replacements where `main` already has a working adapter
2. Mission Control stays native to this repo.
   - no parallel control plane
   - no second orchestration stack
3. Do not make `apps/` the product unit.
   - agents stay the deployable unit
4. Keep `business_id + environment` alive during migration.
   - additive `org_id` / actor context, not destructive cutover
5. Use one canonical live plan on this branch.
   - older plans remain live source inputs, not archived lies

## Phase spine

### Phase 0 — Repoint docs and freeze the combined branch contract

**Goal**
Make this branch the canonical combined scope and repair the mistaken enterprise-plan deprecation.

**Files**
- Modify: `TODO.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- Create: `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md`

**Tasks**
1. Point TODO/CONTEXT/memory at this master plan.
2. Remove the mistaken `Deprecated` marker from the 2026-04-15 enterprise plan.
3. Mark the 2026-04-13 Mission Control orchestration plan and 2026-04-15 enterprise plan as live source inputs for this branch.
4. State that this branch extends current `main` instead of re-implementing past phases.

**Verification**
- `git diff --check`
- `git status --short`

**Exit gate**
This branch has one canonical plan and the enterprise plan is no longer mislabeled as deprecated.

---

### Phase 1 — Validate the current `main` baseline before adding backlog work

**Goal**
Confirm the merged baseline is stable so later enterprise/Mission Control work starts from facts, not old assumptions.

**Files**
No intended code edits in this phase.

**Read / inspect**
- `README.md`
- `CONTEXT.md`
- `memory.md`
- `app/db/client.py`
- `app/db/control_plane_store_supabase.py`
- `app/services/mission_control_service.py`
- `app/api/trigger_callbacks.py`
- `app/services/run_lifecycle_service.py`
- `apps/mission-control/src/`

**Verification**
- `uv run pytest -q`
- optional focused checks if a later phase touches them:
  - `uv run pytest tests/db/test_supabase_control_plane_client.py -q`
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run`

**Exit gate**
Baseline state is green and documented; no backlog phase begins from stale assumptions.

---

### Phase 2 — Org tenancy and actor context

**Goal**
Layer real enterprise tenancy on top of current business/environment scoping without breaking existing flows.

**Key files**
- `app/core/config.py`
- `app/core/dependencies.py`
- `app/models/agents.py`
- `app/models/sessions.py`
- `app/models/permissions.py`
- `app/models/mission_control.py`
- `app/services/agent_registry_service.py`
- `app/services/session_service.py`
- `app/services/permission_service.py`
- `app/services/mission_control_service.py`
- `app/api/agents.py`
- `app/api/sessions.py`
- `app/api/permissions.py`
- `supabase/migrations/*org*`

**Create**
- org / membership / actor models, repos, services, and API routes

**Verification**
- tenant isolation tests
- Mission Control org-scoping tests
- full `uv run pytest -q`

**Exit gate**
One internal org can run agents and Mission Control views without cross-org leakage.

---

### Phase 3 — Agents as deployable units + host-adapter contract

**Goal**
Promote the current managed-agent scaffolding into a real data-backed agent runtime model.

**Scope**
- revisioned registry hardening
- host adapter contract formalization
- publishable revision metadata
- session pinning to immutable revisions
- adapter-specific config envelopes without product-model leakage

**Key files**
- `app/models/agents.py`
- `app/services/agent_registry_service.py`
- `app/services/host_adapter_dispatch_service.py`
- `app/db/agents.py`
- `app/api/agents.py`
- `app/api/host_adapters.py` if needed
- `trigger/src/runtime/*`

**Verification**
- adapter selection tests
- revision pinning tests
- publish/archive/clone regression coverage

**Exit gate**
An agent revision is the executable unit, with host adapter choice explicit and test-covered.

---

### Phase 4 — Enterprise controls

**Goal**
Close the real governance backlog for internal dogfood.

**Scope**
- RBAC completion
- secrets as first-class resources
- append-only audit expectations
- usage accounting visibility
- approval boundaries in Mission Control

**Key files**
- `app/models/rbac.py`
- `app/models/secrets.py`
- `app/models/audit.py`
- `app/models/usage.py`
- `app/services/*rbac*`
- `app/services/secrets_service.py`
- `app/services/audit_service.py`
- `app/services/usage_service.py`
- `app/api/mission_control.py`
- `app/services/mission_control_service.py`
- `apps/mission-control/src/pages/SettingsPage.tsx`

**Verification**
- targeted RBAC/secrets/audit/usage tests
- Mission Control UI typecheck + test + build
- full backend suite

**Exit gate**
Internal operator workflows can inspect and trust approvals, audit, secrets, and usage without repo spelunking.

---

### Phase 5 — Release lifecycle, replay, evaluation, rollback

**Goal**
Make revisions safe to promote and revert.

**Scope**
- draft/candidate/published/deprecated/archived states
- canary/rollback model
- replay lineage and evaluation-gated promotion
- revision/session/run correlation contracts

**Key files**
- `app/models/agents.py`
- `app/models/runs.py`
- `app/services/replay_service.py`
- `app/services/run_lifecycle_service.py`
- `app/services/agent_registry_service.py`
- `app/api/replays.py`
- `app/api/agents.py`
- `apps/mission-control/src/pages/AgentsPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`

**Verification**
- replay lineage tests
- rollout state machine tests
- Mission Control release-panel tests

**Exit gate**
A revision can be published, observed, replayed, evaluated, and rolled back with runtime-owned lineage.

---

### Phase 6 — Productize Mission Control for the internal operator workflow

**Goal**
Finish the operator cockpit as a true control-plane surface instead of a partial shell.

**Scope**
- richer agent detail workflow
- release panels
- host adapter visibility
- secrets/audit/usage surfaces
- org-aware filtering and navigation
- stable UI contracts over runtime-owned read models

**Key files**
- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/lib/api.ts`
- `apps/mission-control/src/lib/fixtures.ts`
- `apps/mission-control/src/pages/*`
- `apps/mission-control/src/components/*`
- `app/services/mission_control_service.py`
- `app/models/mission_control.py`
- `app/api/mission_control.py`

**Verification**
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`
- relevant backend read-model tests

**Exit gate**
Mission Control is sufficient for internal operator dogfood across agents, releases, approvals, audits, and runs.

---

### Phase 7 — Internal catalog first, marketplace later

**Goal**
Prepare distribution without distorting the core model.

**Scope**
- internal install / catalog flow first
- package metadata and templates second
- marketplace later behind explicit flags

**Not allowed yet**
- turning apps into product units
- public marketplace launch before internal dogfood is solid

**Exit gate**
Internal catalog flow works without changing execution semantics.

## What is explicitly deferred

- replacing Trigger.dev as the current production adapter
- public marketplace launch
- any destructive migration that removes current `business_id + environment` usage in one cut
- redoing already-landed Ares CRM runtime phases just because this branch is broader

## Branch completion rule

This branch is for the combined Mission Control + enterprise backlog execution path. Work should land here phase-by-phase, with each phase verified before the next one starts.
