# Ralph Loop Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
>
> **Execution model:** use `gpt-5.3-codex` for the actual work.
>
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** finish the full Ares enterprise-platform implementation roadmap end to end, not just the current phase slice.

**Architecture:** Ares stays the deterministic runtime and integration layer. Mission Control stays the operator cockpit. Agents are the product unit. Skills are reusable procedures. Host runtimes are adapters. Release, governance, catalog, and marketplace behavior all hang off agent revisions and org scope.

**Tech Stack:** FastAPI, Pydantic, Supabase migrations, Python pytest, Trigger.dev, TypeScript, React, Vite, Vitest.

---

## What Ralph loop means

Ralph loop is the overnight execution loop for this repo:
- take one phase at a time
- break every phase into tiny implementation steps
- run the phase gate tests before moving on
- do not declare a phase complete until the gate is green
- use `gpt-5.3-codex` as the work model for implementation tasks

The loop is not allowed to skip phases, merge them into one blob, or call something finished because the UI looked fine once.

---

## Current completion snapshot

| Phase | Status | What is already true |
|---|---|---|
| Phase 0 | Done | product model / architecture language is locked in the repo docs |
| Phase 1 | Done | org tenancy and actor-context plumbing are wired in-memory |
| Phase 2 | Partial | agent / skill / host-adapter baseline exists, but the full adapter contract still needs finish work where the repo says so |
| Phase 3 | Done | RBAC, secrets, audit, and usage controls are implemented in the current worktree |
| Phase 4 | Pending | replay-safe release management is not yet finished |
| Phase 5 | Partial | Mission Control exists as a fixture-backed cockpit, but the full dogfood workflow and governance surfaces still need completion |
| Phase 6 | Pending | internal catalog and marketplace distribution are not built yet |

## Source docs this plan is built from

- `docs/superpowers/specs/Hermes — Instantly Lead Automation Final Spec 2026.md`
- `docs/superpowers/plans/2026-04-16-harris-probate-keep-now-ingestion-plan.md`
- `docs/superpowers/plans/2026-04-16-curative-title-cold-email-machine-plan.md`
- `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`

---

## Phase 0 — Lock product language and architecture boundaries

**Status:** done

### Task 0.1: Lock the product model in docs

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Create: `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- Create: `docs/mission-control-wiki/concepts/agent-platform-product-model.md`
- Create: `docs/mission-control-wiki/concepts/enterprise-agent-governance.md`

**Completed outcome:**
- Ares is framed as an agent platform, not an app platform.
- Mission Control is framed as the operator cockpit.
- Agents are the deployable product unit.
- Skills are reusable procedures.
- Host runtimes are adapters.

**Validation that already passed:**
- docs were updated without contradictions to the runtime/service names
- repo context points to the live plan files instead of stale assumptions

### Task 0.2: Freeze the host-adapter rule

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`

**Completed outcome:**
- Trigger.dev is the first enabled adapter, not the platform identity.
- Codex and Anthropic are treated as future adapter implementations, not forks of the product model.
- Generic agent identity does not leak Trigger-specific fields.

**Validation that already passed:**
- docs and memory agree on the adapter boundary
- the plan file treats adapter-specific config as the only place runtime-specific details belong

### Task 0.3: Freeze the release model

**Files:**
- Modify: `memory.md`
- Modify: `CONTEXT.md`
- Modify: `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`

**Completed outcome:**
- Agent revision = deployable release artifact.
- Session = execution thread pinned to one revision.
- Skill = reusable capability.
- App = UI/operator surface only.

**Validation that already passed:**
- the repo context now separates agent/product rules from surface/UI rules

### Phase 0 gate tests

Run only when docs are edited again:
- `git diff --check`
- read-through consistency check against `README.md`, `CONTEXT.md`, and `memory.md`

**Do not move to Phase 1 unless the architecture language is consistent.**

---

## Phase 1 — Add org tenancy and actor context for internal dogfood

**Status:** done

### Task 1.1: Add the org model

**Files:**
- Create: `supabase/migrations/202604150001_enterprise_org_tenancy.sql`
- Create: `app/models/organizations.py`
- Create: `app/models/actors.py`
- Create: `app/db/organizations.py`
- Create: `app/db/memberships.py`
- Create: `app/services/organization_service.py`
- Create: `app/services/access_service.py`
- Create: `app/api/organizations.py`
- Create: `app/api/memberships.py`

**Subtasks:**
- [x] define organization and membership records
- [x] seed one internal org for dogfood
- [x] preserve the current `business_id` and `environment` contracts while adding `org_id`

**Validation that already passed:**
- org-scoped repository and API tests were added and passed
- same `business_id` in multiple orgs does not leak data

### Task 1.2: Thread org ownership through runtime records

**Files:**
- Modify: `app/models/agents.py`
- Modify: `app/models/sessions.py`
- Modify: `app/models/permissions.py`
- Modify: `app/models/mission_control.py`
- Modify: `app/db/agents.py`
- Modify: `app/db/sessions.py`
- Modify: `app/db/permissions.py`
- Modify: `app/services/agent_registry_service.py`
- Modify: `app/services/session_service.py`
- Modify: `app/services/permission_service.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/agents.py`
- Modify: `app/api/sessions.py`
- Modify: `app/api/permissions.py`

**Subtasks:**
- [x] add `org_id` to agents, sessions, permissions, outcomes, assets, runs, commands, approvals, and Mission Control projections
- [x] keep `business_id` in the current runtime contracts during the transition
- [x] avoid a giant cutover that would break current filters

**Validation that already passed:**
- Mission Control reads respect org scope
- session and turn read models remain stable under org-aware filters

### Task 1.3: Resolve actor context in dependencies

**Files:**
- Modify: `app/core/dependencies.py`
- Modify: `app/main.py`

**Subtasks:**
- [x] resolve the acting org/member/service-account from dependencies
- [x] keep the service-to-service API key path intact
- [x] stop scattering raw header parsing through the routes

**Validation that already passed:**
- service-account requests resolve to org-scoped actors
- session and turn routes stay usable when actor headers are absent

### Task 1.4: Make Mission Control org-aware

**Files:**
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`

**Subtasks:**
- [x] filter Mission Control read models by `org_id` first
- [x] keep `business_id` and `environment` as secondary runtime filters where still needed
- [x] keep the UI usable without exposing org switching everywhere yet

**Validation that already passed:**
- Mission Control turns and read models are scoped correctly in tests
- no cross-org leakage in turn/session contract tests

### Phase 1 gate tests

These were the phase gate tests for the org-tenancy slice:
- `uv run pytest tests/db/test_organizations_repository.py -q`
- `uv run pytest tests/db/test_memberships_repository.py -q`
- `uv run pytest tests/api/test_organizations.py -q`
- `uv run pytest tests/api/test_memberships.py -q`
- `uv run pytest tests/api/test_tenant_scoping.py -q`
- `uv run pytest -q`

**Do not move to Phase 2 unless org isolation and actor scoping are green.**

---

## Phase 2 — Make agents the deployable product unit and formalize host adapters

**Status:** partial

### Task 2.1: Extend the agent record to be product-shaped

**Files:**
- Modify: `app/models/agents.py`
- Modify: `app/db/agents.py`
- Modify: `app/services/agent_registry_service.py`
- Modify: `app/services/session_service.py`
- Modify: `app/services/command_service.py`
- Modify: `app/services/run_service.py`
- Modify: `app/services/hermes_tools_service.py`
- Modify: `app/api/agents.py`
- Modify: `app/api/sessions.py`
- Modify: `app/main.py`
- Modify: `trigger/src/shared/runtimeApi.ts`
- Modify: `trigger/src/runtime/reportRunLifecycle.ts`
- Modify: `trigger/src/runtime/queueKeys.ts`

**Subtasks:**
- [ ] add stable agent slug, owner `org_id`, visibility, lifecycle status, and packaging metadata
- [ ] extend revisions with host kind, adapter config envelope, input schema, output schema, bound skill ids, release notes, and compatibility metadata
- [ ] keep the current revision shape readable by Mission Control and run lifecycle code

**Task-level tests:**
- `uv run pytest tests/api/test_agents.py -q`
- `uv run pytest -q`

### Task 2.2: Introduce a first-class skill registry

**Files:**
- Create: `supabase/migrations/202604150002_agent_registry_and_host_adapters.sql`
- Create: `app/models/skills.py`
- Create: `app/db/skills.py`
- Create: `app/services/skill_registry_service.py`
- Create: `app/api/skills.py`
- Create: `tests/db/test_skills_repository.py`
- Create: `tests/api/test_skills.py`

**Subtasks:**
- [ ] define skill metadata, input/output contracts, and permission requirements
- [ ] make agent revisions reference skill ids instead of embedding procedural config everywhere
- [ ] keep skills reusable across many agents

**Task-level tests:**
- `uv run pytest tests/db/test_skills_repository.py -q`
- `uv run pytest tests/api/test_skills.py -q`
- `uv run pytest -q`

### Task 2.3: Introduce the host-adapter contract

**Files:**
- Create: `app/models/host_adapters.py`
- Create: `app/host_adapters/base.py`
- Create: `app/host_adapters/registry.py`
- Create: `app/host_adapters/trigger_dev.py`
- Create: `app/host_adapters/codex.py`
- Create: `app/host_adapters/anthropic.py`
- Create: `tests/host_adapters/test_host_registry.py`
- Create: `tests/host_adapters/test_trigger_dev_adapter.py`
- Create: `tests/host_adapters/test_disabled_host_adapters.py`

**Subtasks:**
- [ ] define dispatch, status correlation, artifact reporting, and cancellation support in the base adapter
- [ ] implement Trigger.dev as the first real adapter
- [ ] keep Codex and Anthropic adapters disabled or no-op until later phases
- [ ] map host kind to adapter implementation in a registry

**Task-level tests:**
- `uv run pytest tests/host_adapters/test_host_registry.py -q`
- `uv run pytest tests/host_adapters/test_trigger_dev_adapter.py -q`
- `uv run pytest tests/host_adapters/test_disabled_host_adapters.py -q`
- `npx tsc -p trigger/tsconfig.json --noEmit`
- `uv run pytest -q`

### Task 2.4: Move execution dispatch behind the adapter service

**Files:**
- Create: `app/services/agent_execution_service.py`
- Modify: `app/services/run_service.py`
- Modify: `app/services/replay_service.py`
- Modify: `app/services/hermes_tools_service.py`
- Modify: `app/api/trigger_callbacks.py`
- Modify: `trigger/src/runtime/reportRunLifecycle.ts`

**Subtasks:**
- [ ] make `agent_execution_service.py` the only place that turns an agent revision into host execution
- [ ] keep Trigger lifecycle callbacks as one adapter implementation, not the platform contract
- [ ] preserve current run correlation ids through the adapter path

**Task-level tests:**
- `uv run pytest tests/services/test_agent_execution_service.py -q`
- `uv run pytest tests/api/test_trigger_callbacks.py -q`
- `uv run pytest -q`

### Task 2.5: Keep Hermes tools data-backed

**Files:**
- Modify: `app/services/hermes_tools_service.py`

**Subtasks:**
- [ ] derive tool surface from skills and agent revision policy rather than `POLICY_BY_COMMAND` alone
- [ ] preserve backward compatibility for existing command types during migration

**Task-level tests:**
- `uv run pytest tests/hermes_cli/test_tools_config.py -q`
- `uv run pytest -q`

### Phase 2 gate tests

Run the full adapter slice together before moving on:
- `uv run pytest tests/db/test_skills_repository.py -q`
- `uv run pytest tests/api/test_skills.py -q`
- `uv run pytest tests/services/test_agent_execution_service.py -q`
- `uv run pytest tests/host_adapters/test_host_registry.py -q`
- `uv run pytest tests/host_adapters/test_trigger_dev_adapter.py -q`
- `uv run pytest tests/host_adapters/test_disabled_host_adapters.py -q`
- `uv run pytest tests/api/test_agents.py -q`
- `npx tsc -p trigger/tsconfig.json --noEmit`
- `uv run pytest -q`

**Do not move to Phase 3 unless dispatch goes through the adapter registry in tests.**

---

## Phase 3 — Add enterprise controls: RBAC, secrets, audit, usage

**Status:** done

### Task 3.1: Expand permissions into RBAC plus policy overlays

**Files:**
- Modify: `app/core/dependencies.py`
- Modify: `app/models/permissions.py`
- Modify: `app/services/permission_service.py`
- Modify: `app/api/permissions.py`
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/models/outcomes.py`
- Modify: `app/services/outcome_service.py`

**Subtasks:**
- [x] keep per-agent-tool permissions
- [x] add org roles such as `platform_admin`, `org_admin`, `agent_builder`, `operator`, `reviewer`, and `auditor`
- [x] resolve access by combining role grants, org policy, and agent revision policy

**Validation that already passed:**
- unauthorized publish, rollback, and secret-access paths are blocked in tests
- org scoping still works after policy overlays

### Task 3.2: Introduce secrets as first-class org resources

**Files:**
- Create: `supabase/migrations/202604150003_enterprise_controls.sql`
- Create: `app/models/rbac.py`
- Create: `app/models/secrets.py`
- Create: `app/db/rbac.py`
- Create: `app/db/secrets.py`
- Create: `app/services/rbac_service.py`
- Create: `app/services/secret_service.py`
- Create: `app/api/rbac.py`
- Create: `app/api/secrets.py`
- Create: `tests/db/test_rbac_repository.py`
- Create: `tests/db/test_secrets_repository.py`
- Create: `tests/api/test_rbac.py`
- Create: `tests/api/test_secrets.py`

**Subtasks:**
- [x] store secret metadata and secret references separately from agent revisions
- [x] bind named secret references instead of raw plaintext values
- [x] add API redaction rules
- [x] emit audit events for secret reads and updates

**Validation that already passed:**
- secret values never return in full from API responses
- secret access is auditable and redacted

### Task 3.3: Introduce append-only audit

**Files:**
- Create: `app/models/audit.py`
- Create: `app/db/audit.py`
- Create: `app/services/audit_service.py`
- Create: `app/api/audit.py`
- Create: `tests/db/test_audit_repository.py`
- Create: `tests/api/test_audit.py`

**Subtasks:**
- [x] capture agent create/publish/archive/clone/rollback, session create, permission updates, secret access, approval actions, and host dispatch events
- [x] add correlation fields for `org_id`, `agent_id`, `agent_revision_id`, `session_id`, `run_id`, and actor
- [x] keep audit append-only

**Validation that already passed:**
- audit rows append, not mutate
- sensitive metadata is scrubbed before it reaches read surfaces

### Task 3.4: Introduce usage accounting

**Files:**
- Create: `app/models/usage.py`
- Create: `app/db/usage.py`
- Create: `app/services/usage_service.py`
- Create: `app/api/usage.py`
- Create: `tests/db/test_usage_repository.py`
- Create: `tests/api/test_usage.py`

**Subtasks:**
- [x] track per-org and per-agent usage for runs, sessions, tool invocations, and provider calls
- [x] keep provider-specific metering extensible
- [x] make Mission Control show the summaries instead of hiding the numbers in logs

**Validation that already passed:**
- usage aggregation works across more than one host adapter kind
- summary numbers stay accurate when responses are paginated

### Task 3.5: Surface governance in Mission Control

**Files:**
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`

**Subtasks:**
- [x] extend read models so the UI can show secret health, audit events, and usage summaries
- [x] keep the operator cockpit backend-driven
- [x] redact thread context and sensitive metadata before rendering

**Validation that already passed:**
- Mission Control shows the governance state without leaking secrets
- audit, usage, and secret-binding surfaces stay queryable by revision

### Phase 3 gate tests

These were the phase gate tests for the enterprise-controls slice:
- `uv run pytest tests/db/test_rbac_repository.py -q`
- `uv run pytest tests/db/test_secrets_repository.py -q`
- `uv run pytest tests/db/test_audit_repository.py -q`
- `uv run pytest tests/db/test_usage_repository.py -q`
- `uv run pytest tests/api/test_rbac.py -q`
- `uv run pytest tests/api/test_secrets.py -q`
- `uv run pytest tests/api/test_audit.py -q`
- `uv run pytest tests/api/test_usage.py -q`
- `uv run pytest -q`

**Do not move to Phase 4 unless the internal org can govern agent publishing and execution in tests.**

---

## Phase 4 — Add replay-safe release management, evaluations, and rollback

**Status:** pending

### Task 4.1: Add revision promotion states

**Files:**
- Modify: `app/models/agents.py`
- Modify: `app/models/runs.py`
- Modify: `app/models/run_events.py`
- Modify: `app/models/outcomes.py`
- Modify: `app/db/agents.py`
- Modify: `app/services/agent_registry_service.py`
- Modify: `app/services/replay_service.py`
- Modify: `app/services/run_lifecycle_service.py`
- Modify: `app/services/outcome_service.py`
- Modify: `app/api/agents.py`
- Modify: `app/api/replays.py`
- Modify: `app/api/trigger_callbacks.py`
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Create: `supabase/migrations/202604150004_agent_release_management.sql`
- Create: `app/models/release_management.py`
- Create: `app/db/release_management.py`
- Create: `app/services/release_management_service.py`
- Create: `app/api/release_management.py`
- Create: `tests/db/test_release_management_repository.py`
- Create: `tests/api/test_release_management.py`
- Create: `tests/api/test_replays.py`
- Create: `tests/api/test_trigger_callbacks.py`
- Create: `tests/api/test_outcomes.py`

**Subtasks:**
- [ ] support `draft`, `candidate`, `published`, `deprecated`, `archived`, and `rolled_back` lifecycle markers
- [ ] add release channels for internal dogfood and later marketplace distribution
- [ ] keep release state tied to revisions, not loose agent records

**Task-level tests:**
- `uv run pytest tests/db/test_release_management_repository.py -q`
- `uv run pytest tests/api/test_release_management.py -q`

### Task 4.2: Add canary and rollback semantics

**Subtasks:**
- [ ] promote a candidate revision safely
- [ ] rollback to a prior published revision without rewriting history
- [ ] emit a new release event and active-pointer change instead of mutating old rows

**Task-level tests:**
- `uv run pytest tests/api/test_trigger_callbacks.py -q`
- `uv run pytest tests/api/test_replays.py -q`
- `uv run pytest tests/api/test_release_management.py -q`

### Task 4.3: Keep sessions pinned

**Subtasks:**
- [ ] keep existing sessions on the revision that created them
- [ ] let new sessions inherit the current active revision only after promotion succeeds
- [ ] protect historical session lineage during rollback

**Task-level tests:**
- `uv run pytest tests/api/test_replays.py -q`
- `uv run pytest tests/api/test_release_management.py -q`

### Task 4.4: Expand replay lineage

**Subtasks:**
- [ ] add replay reason, parent-child lineage, triggering actor, source revision id, and release version context
- [ ] keep replay runtime-owned, not host-owned

**Task-level tests:**
- `uv run pytest tests/api/test_replays.py -q`
- `uv run pytest tests/api/test_trigger_callbacks.py -q`

### Task 4.5: Tie outcomes to release decisions

**Subtasks:**
- [ ] use outcomes as the seed for evaluation loops
- [ ] require release evaluation summaries for promotion or rollback when appropriate
- [ ] block promotion if the evaluation fails

**Task-level tests:**
- `uv run pytest tests/api/test_outcomes.py -q`
- `uv run pytest tests/api/test_release_management.py -q`

### Phase 4 gate tests

Run the release-management slice together before moving on:
- `uv run pytest tests/db/test_release_management_repository.py -q`
- `uv run pytest tests/api/test_release_management.py -q`
- `uv run pytest tests/api/test_replays.py -q`
- `uv run pytest tests/api/test_trigger_callbacks.py -q`
- `uv run pytest tests/api/test_outcomes.py -q`
- `uv run pytest -q`

**Do not move to Phase 5 unless a published revision can be safely promoted, replayed, and rolled back in tests without losing session lineage.**

---

## Phase 5 — Productize the internal dogfood workflow in Mission Control

**Status:** partial

### Task 5.1: Reorder the internal information architecture

**Files:**
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/api.ts`
- Modify: `apps/mission-control/src/components/MissionControlShell.tsx`
- Modify: `apps/mission-control/src/pages/AgentsPage.tsx`
- Modify: `apps/mission-control/src/pages/RunsPage.tsx`
- Modify: `apps/mission-control/src/pages/SettingsPage.tsx`
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`

**Subtasks:**
- [ ] make agents a first-class navigation surface
- [ ] keep dashboard, inbox, approvals, and runs as operator views around agents
- [ ] keep the UI thin and backend-owned

**Task-level tests:**
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`

### Task 5.2: Add the internal agent lifecycle workflow

**Files:**
- Create: `apps/mission-control/src/components/AgentRegistryTable.tsx`
- Create: `apps/mission-control/src/components/RunTimeline.tsx`
- Create: `apps/mission-control/src/components/ContextPanel.tsx`
- Create: `apps/mission-control/src/components/OrgSwitcher.tsx`
- Create: `apps/mission-control/src/components/AgentReleasePanel.tsx`
- Create: `apps/mission-control/src/components/SkillBindingsPanel.tsx`
- Create: `apps/mission-control/src/components/HostAdapterBadge.tsx`
- Create: `apps/mission-control/src/pages/AgentDetailPage.tsx`
- Create: `apps/mission-control/src/pages/AgentDetailPage.test.tsx`

**Subtasks:**
- [ ] create agent
- [ ] bind skills
- [ ] select host adapter
- [ ] bind secrets and assets
- [ ] publish a candidate revision
- [ ] run and test it
- [ ] inspect audit, usage, and outcomes
- [ ] rollback if needed

**Task-level tests:**
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest tests/api/test_mission_control.py -q`

### Task 5.3: Surface host-adapter visibility

**Files:**
- Create: `apps/mission-control/src/components/HostAdapterBadge.tsx`
- Modify: `apps/mission-control/src/components/AgentReleasePanel.tsx`
- Modify: `apps/mission-control/src/pages/AgentDetailPage.tsx`

**Subtasks:**
- [ ] show which host adapter a revision uses
- [ ] show compatibility warnings when an agent references a disabled adapter
- [ ] show Trigger-specific runtime details as adapter details, not as platform identity

**Task-level tests:**
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`

### Task 5.4: Add governance surfaces

**Files:**
- Create: `apps/mission-control/src/components/SecretHealthPanel.tsx`
- Create: `apps/mission-control/src/components/AuditTimeline.tsx`
- Create: `apps/mission-control/src/components/UsageSummaryCard.tsx`
- Create: `apps/mission-control/src/pages/UsagePage.tsx`
- Create: `apps/mission-control/src/pages/AuditPage.tsx`
- Create: `apps/mission-control/src/pages/SecretsPage.tsx`
- Create: `apps/mission-control/src/pages/UsagePage.test.tsx`
- Create: `apps/mission-control/src/pages/AuditPage.test.tsx`

**Subtasks:**
- [ ] expose secret health
- [ ] expose the audit timeline
- [ ] expose usage summaries
- [ ] expose release status and rollback controls

**Task-level tests:**
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest tests/api/test_mission_control.py -q`

### Task 5.5: Keep backend ownership of read models

**Subtasks:**
- [ ] have the UI render typed backend responses only
- [ ] avoid inventing frontend-only truth models
- [ ] keep business logic out of React components

**Task-level tests:**
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`

### Phase 5 gate tests

Run the full Mission Control slice together before moving on:
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest tests/api/test_mission_control.py -q`
- `uv run pytest -q`

**Do not move to Phase 6 unless an internal operator can complete the agent lifecycle from Mission Control without touching raw database state.**

---

## Phase 6 — Add internal catalog first, then marketplace distribution

**Status:** pending

### Task 6.1: Add internal catalog metadata

**Files:**
- Create: `supabase/migrations/202604150005_agent_catalog_and_marketplace.sql`
- Create: `app/models/catalog.py`
- Create: `app/models/agent_installs.py`
- Create: `app/db/catalog.py`
- Create: `app/db/agent_installs.py`
- Create: `app/services/catalog_service.py`
- Create: `app/services/agent_install_service.py`
- Create: `app/api/catalog.py`
- Create: `app/api/agent_installs.py`
- Create: `apps/mission-control/src/pages/CatalogPage.tsx`
- Create: `apps/mission-control/src/components/AgentInstallWizard.tsx`
- Create: `apps/mission-control/src/pages/CatalogPage.test.tsx`
- Create: `tests/db/test_catalog_repository.py`
- Create: `tests/db/test_agent_install_repository.py`
- Create: `tests/api/test_catalog.py`
- Create: `tests/api/test_agent_installs.py`

**Subtasks:**
- [ ] point catalog entries at agent revisions, not apps
- [ ] include host compatibility, required skills, required secret bindings, release channel, and install instructions
- [ ] keep source-revision lineage intact

**Task-level tests:**
- `uv run pytest tests/db/test_catalog_repository.py -q`
- `uv run pytest tests/api/test_catalog.py -q`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`

### Task 6.2: Add install flows

**Subtasks:**
- [ ] install a catalog entry into an org-scoped installed-agent record or cloned revision
- [ ] preserve source revision lineage and compatibility data
- [ ] fail clearly before runtime when the host or secret requirements do not match

**Task-level tests:**
- `uv run pytest tests/db/test_agent_install_repository.py -q`
- `uv run pytest tests/api/test_agent_installs.py -q`
- `npm --prefix apps/mission-control run test -- --run`

### Task 6.3: Add marketplace readiness controls

**Subtasks:**
- [ ] support `internal`, `private_catalog`, `marketplace_candidate`, and `marketplace_published`
- [ ] require enterprise controls and release checks before a listing moves beyond internal catalog
- [ ] keep public/partner distribution disabled by default

**Task-level tests:**
- `uv run pytest tests/api/test_catalog.py -q`
- `uv run pytest tests/api/test_agent_installs.py -q`
- `uv run pytest -q`

### Task 6.4: Preserve host portability

**Subtasks:**
- [ ] declare compatible host adapters in catalog metadata
- [ ] prevent an incompatible host install before runtime starts
- [ ] keep the Trigger/Codex/Anthropic seam explicit

**Task-level tests:**
- `uv run pytest tests/api/test_catalog.py -q`
- `uv run pytest tests/api/test_agent_installs.py -q`

### Task 6.5: Keep marketplace behind a feature flag until dogfood says it is safe

**Subtasks:**
- [ ] ship internal catalog first
- [ ] keep public or partner marketplace disabled by default
- [ ] only enable exposure when dogfood data says it is safe

**Task-level tests:**
- `uv run pytest tests/api/test_catalog.py -q`
- `uv run pytest tests/api/test_agent_installs.py -q`
- `npm --prefix apps/mission-control run test -- --run`

### Phase 6 gate tests

Run the distribution slice together before calling the whole roadmap done:
- `uv run pytest tests/db/test_catalog_repository.py -q`
- `uv run pytest tests/db/test_agent_install_repository.py -q`
- `uv run pytest tests/api/test_catalog.py -q`
- `uv run pytest tests/api/test_agent_installs.py -q`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest -q`

**Do not move to the definition of done until internal catalog installs are stable and the enterprise controls are enforced in staging.**

---

## Cross-phase implementation rules

### 1. Migration rules

- Never rewrite already-applied migrations in place.
- Use additive migrations only.
- Carry enough correlation fields for org, agent, revision, session, and run tracing.

### 2. Adapter rules

- All runtime dispatch must go through the adapter registry and `app/services/agent_execution_service.py`.
- Trigger-specific details belong under the Trigger adapter or Trigger callback contract.
- Codex and Anthropic runtimes should be adapter implementations, not forks of agent logic.

### 3. Product rules

- Do not add a new `apps/<agent-name>/` surface for each agent.
- Agents are records and revisions in the platform, surfaced through Mission Control and catalog APIs.
- Skills stay reusable and composable across many agents.

### 4. Testing rules

Every phase should leave the repo green across:
- `uv run pytest -q`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `npx tsc -p trigger/tsconfig.json --noEmit`

### 5. Rollout rules

- Dogfood in one internal org first.
- Then stage with multi-org test data.
- Then private internal catalog.
- Then marketplace candidate.
- Then external distribution.

---

## Definition of done

This plan is complete when Ares can truthfully say:
- agents are the primary product unit
- Mission Control is the internal operator cockpit, not the product boundary
- Trigger.dev is an adapter, not the platform identity
- org tenancy, RBAC, secrets, audit, usage, replay, and rollback are first-class
- agent revisions can be published, supervised, replayed, and rolled back safely
- skills are reusable across agents
- Codex and Anthropic runtimes have a preserved adapter seam even if not yet enabled
- internal catalog distribution works before marketplace exposure

---

## Ralph loop execution notes

When this plan is handed to workers:
1. pick the next incomplete task
2. write the failing tests first
3. make the smallest code change that satisfies the tests
4. run the phase gate suite again
5. only then move forward

If a phase is marked done above, do not reopen it unless a regression appears or a doc conflict needs correction.
