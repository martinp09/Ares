# Ares Enterprise Agent Platform Implementation Plan

> **Deprecated:** superseded by `docs/superpowers/plans/2026-04-20-ralph-loop-full-implementation-plan.md`.
>
> Execution root: `/home/workspace/Hermes-Central-Command`
>
> This document is a plan only. It intentionally describes the next implementation stage in exact, executable steps without making code changes itself.

## Goal

Turn Ares from a control-plane scaffold into a real enterprise agent platform that is:
- optimized for internal dogfood first
- hardened for enterprise controls second
- packaged for marketplace distribution last

The product model must stay explicit:
- agents are the primary product unit
- skills are reusable procedures that agents bind to
- apps are operator surfaces, not the product unit
- host runtimes are swappable adapters
- Trigger.dev is current infrastructure, not the permanent backbone contract

## Current Baseline

The repo already contains:
- in-memory agent registry and revisions in `app/models/agents.py`, `app/db/agents.py`, `app/services/agent_registry_service.py`, and `app/api/agents.py`
- in-memory sessions in `app/models/sessions.py`, `app/db/sessions.py`, `app/services/session_service.py`, and `app/api/sessions.py`
- in-memory permission policy in `app/models/permissions.py`, `app/db/permissions.py`, `app/services/permission_service.py`, and `app/api/permissions.py`
- connect-later agent assets in `app/models/agent_assets.py`, `app/db/agent_assets.py`, `app/services/agent_asset_service.py`, and `app/api/agent_assets.py`
- Mission Control read models in `app/models/mission_control.py`, `app/services/mission_control_service.py`, and `app/api/mission_control.py`
- Trigger lifecycle reporting seams in `app/api/trigger_callbacks.py`, `app/services/run_lifecycle_service.py`, `trigger/src/runtime/reportRunLifecycle.ts`, and `trigger/src/shared/runtimeApi.ts`
- a placeholder managed-agent migration in `supabase/migrations/202604130003_mission_control_managed_agents.sql`
- a native Mission Control shell in `apps/mission-control/src/components/MissionControlShell.tsx`

This plan assumes those surfaces remain the starting point rather than being rewritten from scratch.

## Non-Negotiable Platform Rules

1. Do not make `apps/` the product model.
   - `apps/mission-control/` stays the operator cockpit.
   - No new top-level app should become the canonical packaging unit for agents.

2. Preserve platform-agnostic execution.
   - Introduce a formal host-adapter contract.
   - Implement Trigger.dev as the first production adapter.
   - Add Codex and Anthropic runtime adapters behind the same interface later.
   - Do not leak Trigger-specific fields into agent definitions unless they live under adapter-specific config.

3. Keep the current scope key alive during migration.
   - Preserve `business_id` and `environment` in run-time contracts while adding org-level tenancy.
   - Add `org_id` and actor context without breaking current Mission Control filters in one giant cutover.

4. Internal dogfood first.
   - First ship an internal single-org experience with real auth, secrets, audit, rollback, and usage.
   - Only after that should the platform expose install/publish/distribute marketplace flows.

5. Agents own release lifecycle.
   - Publish, archive, clone, replay, evaluate, canary, and rollback must all hang off agent revisions.
   - Sessions must stay pinned to the revision they started on.

## Target End State

A developer should be able to:
- create an org
- define an agent with versioned revisions
- bind reusable skills
- choose a host adapter
- bind org-scoped secrets and assets
- publish the revision
- run it through Mission Control
- inspect usage, audit, approvals, replay, and rollback history
- package it into an internal catalog entry
- later promote it to marketplace distribution without changing the core execution model

## Recommended Delivery Order

1. Phase 0: lock product language and architecture boundaries
2. Phase 1: add org tenancy and actor context for internal dogfood
3. Phase 2: make agents the primary deployable unit and introduce host adapters
4. Phase 3: add enterprise controls: RBAC, secrets, audit, usage
5. Phase 4: add replay-safe release management, evaluations, and rollback
6. Phase 5: productize the internal Mission Control dogfood workflow
7. Phase 6: add catalog and marketplace distribution

Do not start Phase 6 before Phases 1 through 5 are green in staging.

---

## Phase 0 — Lock the product model and architecture contract

### Goal

Make the repo explicit about the future model before implementation work spreads across Python, SQL, Trigger, and the Mission Control UI.

### Files

Modify:
- `README.md`
- `CONTEXT.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-13-hermes-mission-control-architecture-design.md`
- `docs/superpowers/specs/2026-04-13-hermes-mission-control-ui-design.md`
- `docs/mission-control-wiki/index.md`
- `docs/mission-control-wiki/concepts/agentic-first-command-center.md`

Create:
- `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/enterprise-agent-governance.md`

### Tasks

1. Rewrite the top-level product language.
   - State that Ares is an agent platform and Mission Control is its internal operator shell.
   - State that agents, not apps, are the product unit.
   - State that skills are reusable procedures and host runtimes are adapters.

2. Freeze the host-adapter rule.
   - Define one runtime execution contract shared by Trigger.dev, Codex, and Anthropic runtimes.
   - Make Trigger.dev the only enabled production adapter in the first implementation pass.
   - Forbid direct runtime-specific logic in `app/models/agents.py` outside adapter config envelopes.

3. Freeze the release model.
   - Agent revision = deployable release artifact.
   - Session = execution thread pinned to one revision.
   - Skill = reusable capability referenced by agents.
   - App = UI/operator surface only.

4. Document the migration boundary.
   - Keep `business_id` + `environment` operating during the transition.
   - Add `org_id` as the enterprise parent scope.
   - Use additive schema changes only.

### Tests / Verification

- Read-through only in this phase.
- Ensure the new docs do not contradict:
  - `app/models/agents.py`
  - `app/services/agent_registry_service.py`
  - `app/services/session_service.py`
  - `trigger/src/runtime/reportRunLifecycle.ts`

### Documentation Updates

- Update `README.md` to describe the product as an enterprise agent platform.
- Update `CONTEXT.md` and `memory.md` to point to the new spec.
- Add wiki pages that define the agent/skill/host/app distinction.

### Exit Gate

Do not implement schema or API changes until this language is consistent in docs.

---

## Phase 1 — Add org tenancy and actor context for internal dogfood

### Goal

Introduce enterprise tenancy in a way that preserves the current `business_id` + `environment` workflow while enabling internal dogfood under a real org and actor model.

### Files

Modify:
- `app/core/config.py`
- `app/core/dependencies.py`
- `app/main.py`
- `app/models/agents.py`
- `app/models/sessions.py`
- `app/models/permissions.py`
- `app/models/mission_control.py`
- `app/db/agents.py`
- `app/db/sessions.py`
- `app/db/permissions.py`
- `app/services/agent_registry_service.py`
- `app/services/session_service.py`
- `app/services/permission_service.py`
- `app/services/mission_control_service.py`
- `app/api/agents.py`
- `app/api/sessions.py`
- `app/api/permissions.py`

Create:
- `supabase/migrations/202604150001_enterprise_org_tenancy.sql`
- `app/models/organizations.py`
- `app/models/actors.py`
- `app/db/organizations.py`
- `app/db/memberships.py`
- `app/services/organization_service.py`
- `app/services/access_service.py`
- `app/api/organizations.py`
- `app/api/memberships.py`
- `tests/db/test_organizations_repository.py`
- `tests/db/test_memberships_repository.py`
- `tests/api/test_organizations.py`
- `tests/api/test_memberships.py`
- `tests/api/test_tenant_scoping.py`

### Tasks

1. Create the org model.
   - Add organizations, memberships, and actor records.
   - Seed one internal org for dogfood.
   - Preserve the current `business_id` and `environment` filters on runtime objects.

2. Thread org ownership into current managed-agent records.
   - Add `org_id` to agents, sessions, permissions, outcomes, assets, runs, commands, approvals, and Mission Control projections.
   - Do not remove `business_id` from current contracts yet.

3. Resolve actor context in dependencies.
   - Extend `app/core/dependencies.py` so requests resolve the acting org/member/service account.
   - Keep the current runtime API key path for service-to-service calls.
   - Add a structured actor object rather than scattering raw headers across routes.

4. Make Mission Control org-aware.
   - Update read models and query services so the UI can filter by `org_id` first, then by `business_id` and `environment`.
   - Keep the current UI usable while org switching is not yet exposed broadly.

5. Add staging-safe migration strategy.
   - Add the new tenancy tables and columns additively.
   - Do not modify old applied migrations in place.
   - Leave `supabase/migrations/202604130003_mission_control_managed_agents.sql` untouched as historical scaffold; supersede it with new additive migrations.

### Tests / Verification

Run:
- `uv run pytest tests/db/test_organizations_repository.py -q`
- `uv run pytest tests/db/test_memberships_repository.py -q`
- `uv run pytest tests/api/test_organizations.py -q`
- `uv run pytest tests/api/test_memberships.py -q`
- `uv run pytest tests/api/test_tenant_scoping.py -q`
- `uv run pytest -q`

Add explicit assertions for:
- cross-org isolation
- same `business_id` in two orgs not leaking data
- Mission Control reads respecting org scope
- service-account requests resolving to org-scoped actors

### Documentation Updates

Modify:
- `README.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/enterprise-agent-governance.md`

Document:
- org > business/environment scoping hierarchy
- actor resolution rules
- internal dogfood seed org assumptions

### Exit Gate

Before continuing, one internal org must be able to create agents, sessions, and permissions without leaking into another org in tests.

---

## Phase 2 — Make agents the deployable product unit and formalize host adapters

### Goal

Turn the current agent revision scaffold into a real deployable agent package model with reusable skills and a swappable host-adapter layer.

### Files

Modify:
- `app/models/agents.py`
- `app/db/agents.py`
- `app/services/agent_registry_service.py`
- `app/services/session_service.py`
- `app/services/command_service.py`
- `app/services/run_service.py`
- `app/services/hermes_tools_service.py`
- `app/api/agents.py`
- `app/api/sessions.py`
- `app/main.py`
- `trigger/src/shared/runtimeApi.ts`
- `trigger/src/runtime/reportRunLifecycle.ts`
- `trigger/src/runtime/queueKeys.ts`

Create:
- `supabase/migrations/202604150002_agent_registry_and_host_adapters.sql`
- `app/models/skills.py`
- `app/models/host_adapters.py`
- `app/db/skills.py`
- `app/services/skill_registry_service.py`
- `app/services/agent_execution_service.py`
- `app/api/skills.py`
- `app/host_adapters/base.py`
- `app/host_adapters/registry.py`
- `app/host_adapters/trigger_dev.py`
- `app/host_adapters/codex.py`
- `app/host_adapters/anthropic.py`
- `tests/db/test_skills_repository.py`
- `tests/api/test_skills.py`
- `tests/api/test_agents.py`
- `tests/services/test_agent_execution_service.py`
- `tests/host_adapters/test_host_registry.py`
- `tests/host_adapters/test_trigger_dev_adapter.py`
- `tests/host_adapters/test_disabled_host_adapters.py`

### Tasks

1. Extend the agent record to be product-shaped.
   - Add stable agent slug, owner `org_id`, visibility, lifecycle status, and packaging metadata.
   - Extend revisions to include:
     - host adapter kind
     - host adapter config envelope
     - input schema
     - output schema
     - bound skill ids
     - release notes
     - compatibility metadata

2. Introduce a first-class skill registry.
   - Skills are reusable procedures, not agent variants.
   - Define skill metadata, input/output contracts, and permission requirements.
   - Keep agent revisions referencing skill ids rather than embedding ad hoc procedural config everywhere.

3. Introduce the host-adapter contract.
   - `app/host_adapters/base.py` defines the interface for dispatch, status correlation, artifact reporting, and cancellation support.
   - `app/host_adapters/trigger_dev.py` implements the first real adapter.
   - `app/host_adapters/codex.py` and `app/host_adapters/anthropic.py` implement the same interface but remain disabled or no-op until later phases.
   - `app/host_adapters/registry.py` maps an agent revision’s host kind to the adapter implementation.

4. Move execution dispatch behind the adapter service.
   - `app/services/agent_execution_service.py` should be the only service that turns an agent revision into host execution.
   - `app/services/run_service.py` should request execution through the adapter service instead of coupling directly to Trigger semantics.
   - Preserve current Trigger lifecycle callbacks, but treat them as one adapter’s lifecycle implementation.

5. Keep Hermes tools data-backed.
   - Update `app/services/hermes_tools_service.py` so the tool surface can be derived from skills and agent revision policy rather than from `POLICY_BY_COMMAND` alone.
   - Keep backward compatibility for existing command types during migration.

### Tests / Verification

Run:
- `uv run pytest tests/db/test_skills_repository.py -q`
- `uv run pytest tests/api/test_skills.py -q`
- `uv run pytest tests/services/test_agent_execution_service.py -q`
- `uv run pytest tests/host_adapters/test_host_registry.py -q`
- `uv run pytest tests/host_adapters/test_trigger_dev_adapter.py -q`
- `uv run pytest tests/host_adapters/test_disabled_host_adapters.py -q`
- `uv run pytest tests/api/test_agents.py -q`
- `npx tsc -p trigger/tsconfig.json --noEmit`
- `uv run pytest -q`

Add explicit assertions for:
- agent revision dispatch chooses the correct adapter
- Trigger.dev adapter preserves current run correlation ids
- Codex and Anthropic adapters can register without breaking runtime boot
- skills remain reusable across multiple agents
- sessions remain pinned to the originating revision even after a newer revision publishes

### Documentation Updates

Modify:
- `README.md`
- `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/agentic-first-command-center.md`

Document:
- agent vs skill vs host adapter responsibilities
- Trigger.dev as current adapter, not platform identity
- compatibility rules for future Codex and Anthropic runtimes

### Exit Gate

Before continuing, the platform must be able to define an agent revision that names a host kind and bound skills, and the runtime must dispatch through the adapter registry in tests.

---

## Phase 3 — Add enterprise controls: RBAC, secrets, audit, usage

### Goal

Add the controls that make the platform enterprise-capable for internal dogfood: role-based access, secrets management, append-only audit, and usage accounting.

### Files

Modify:
- `app/core/dependencies.py`
- `app/models/permissions.py`
- `app/services/permission_service.py`
- `app/api/permissions.py`
- `app/models/mission_control.py`
- `app/services/mission_control_service.py`
- `app/models/outcomes.py`
- `app/services/outcome_service.py`

Create:
- `supabase/migrations/202604150003_enterprise_controls.sql`
- `app/models/rbac.py`
- `app/models/secrets.py`
- `app/models/audit.py`
- `app/models/usage.py`
- `app/db/rbac.py`
- `app/db/secrets.py`
- `app/db/audit.py`
- `app/db/usage.py`
- `app/services/rbac_service.py`
- `app/services/secret_service.py`
- `app/services/audit_service.py`
- `app/services/usage_service.py`
- `app/api/rbac.py`
- `app/api/secrets.py`
- `app/api/audit.py`
- `app/api/usage.py`
- `tests/db/test_rbac_repository.py`
- `tests/db/test_secrets_repository.py`
- `tests/db/test_audit_repository.py`
- `tests/db/test_usage_repository.py`
- `tests/api/test_rbac.py`
- `tests/api/test_secrets.py`
- `tests/api/test_audit.py`
- `tests/api/test_usage.py`

### Tasks

1. Expand permissions into RBAC plus policy overlays.
   - Keep per-agent-tool permissions.
   - Add org roles such as `platform_admin`, `org_admin`, `agent_builder`, `operator`, `reviewer`, and `auditor`.
   - Resolve final access by combining role grants, org policy, and agent revision policy.

2. Introduce secrets as first-class org resources.
   - Store secret metadata and secret references separately from agent revisions.
   - Agent revisions should bind named secret references, not raw plaintext values.
   - Build redaction rules into API models.
   - Ensure secret reads and updates emit audit events.

3. Introduce append-only audit.
   - Capture agent creation, publish, archive, clone, rollback, session create, permission updates, secret access, approval actions, and host dispatch events.
   - Add correlation fields for `org_id`, `agent_id`, `agent_revision_id`, `session_id`, `run_id`, and actor.

4. Introduce usage accounting.
   - Track per-org and per-agent usage for runs, sessions, tool invocations, and provider calls.
   - Keep provider-specific metering extensible so Trigger, Codex, and Anthropic runtimes can all report through the same usage model.

5. Surface governance in Mission Control.
   - Extend read models so the UI can show secret health, audit events, and usage summaries.
   - Keep the operator cockpit backend-driven.

### Tests / Verification

Run:
- `uv run pytest tests/db/test_rbac_repository.py -q`
- `uv run pytest tests/db/test_secrets_repository.py -q`
- `uv run pytest tests/db/test_audit_repository.py -q`
- `uv run pytest tests/db/test_usage_repository.py -q`
- `uv run pytest tests/api/test_rbac.py -q`
- `uv run pytest tests/api/test_secrets.py -q`
- `uv run pytest tests/api/test_audit.py -q`
- `uv run pytest tests/api/test_usage.py -q`
- `uv run pytest -q`

Add explicit assertions for:
- roles blocking unauthorized publish/rollback/secret access
- secret values never returning in full from API responses
- audit tables being append-only
- usage aggregation working across more than one host adapter kind

### Documentation Updates

Modify:
- `README.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/enterprise-agent-governance.md`

Document:
- role definitions
- secret binding rules
- audit event taxonomy
- usage dimensions and aggregation model

### Exit Gate

Before continuing, the internal org must be able to govern agent publishing and execution with roles, secrets, audit logs, and usage summaries in tests.

---

## Phase 4 — Add replay-safe release management, evaluations, and rollback

### Goal

Make agent releases safe enough for real enterprise operations by adding revision promotion rules, canary/rollback support, replay lineage, and evaluation outcomes.

### Files

Modify:
- `app/models/agents.py`
- `app/models/runs.py`
- `app/models/run_events.py`
- `app/models/outcomes.py`
- `app/db/agents.py`
- `app/services/agent_registry_service.py`
- `app/services/replay_service.py`
- `app/services/run_lifecycle_service.py`
- `app/services/outcome_service.py`
- `app/api/agents.py`
- `app/api/replays.py`
- `app/api/trigger_callbacks.py`
- `app/models/mission_control.py`
- `app/services/mission_control_service.py`

Create:
- `supabase/migrations/202604150004_agent_release_management.sql`
- `app/models/release_management.py`
- `app/db/release_management.py`
- `app/services/release_management_service.py`
- `app/api/release_management.py`
- `tests/db/test_release_management_repository.py`
- `tests/api/test_release_management.py`
- `tests/api/test_replays.py`
- `tests/api/test_trigger_callbacks.py`
- `tests/api/test_outcomes.py`

### Tasks

1. Add revision promotion states.
   - Support `draft`, `candidate`, `published`, `deprecated`, `archived`, and `rolled_back` or equivalent lifecycle markers.
   - Add release channels for internal dogfood and later marketplace distribution.

2. Add canary and rollback semantics.
   - Allow controlled promotion of a new revision.
   - Support safe rollback to a prior known-good published revision.
   - Ensure rollback never mutates history; it creates a new release event and active pointer change.

3. Keep sessions pinned.
   - Existing sessions continue on the revision that created them.
   - New sessions inherit the current active revision only after release promotion succeeds.

4. Expand replay lineage.
   - Add replay reason, parent-child lineage, triggering actor, source revision id, and release version context.
   - Ensure replay is runtime-owned, not host-owned.

5. Tie outcomes to release decisions.
   - Use `app/models/outcomes.py` and `app/services/outcome_service.py` as the seed for evaluation loops.
   - Require release evaluation summaries for promotion or rollback where appropriate.

### Tests / Verification

Run:
- `uv run pytest tests/db/test_release_management_repository.py -q`
- `uv run pytest tests/api/test_release_management.py -q`
- `uv run pytest tests/api/test_replays.py -q`
- `uv run pytest tests/api/test_trigger_callbacks.py -q`
- `uv run pytest tests/api/test_outcomes.py -q`
- `uv run pytest -q`

Add explicit assertions for:
- rollback changes the active revision without rewriting prior revision history
- replay records preserve original and new revision context
- sessions remain pinned after rollback
- evaluation failures can block promotion

### Documentation Updates

Modify:
- `README.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/enterprise-agent-governance.md`

Document:
- release states
- replay and rollback rules
- evaluation requirements for promotion

### Exit Gate

Before continuing, a published agent revision must be safely promotable, replayable, and rollbackable in tests without losing session lineage.

---

## Phase 5 — Productize the internal dogfood workflow in Mission Control

### Goal

Make Mission Control the internal dogfood surface for building, publishing, supervising, and rolling back agents, while keeping agents as the platform’s primary product unit.

### Files

Modify:
- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/lib/api.ts`
- `apps/mission-control/src/components/MissionControlShell.tsx`
- `apps/mission-control/src/components/AgentRegistryTable.tsx`
- `apps/mission-control/src/components/RunTimeline.tsx`
- `apps/mission-control/src/components/ContextPanel.tsx`
- `apps/mission-control/src/pages/AgentsPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`
- `apps/mission-control/src/pages/SettingsPage.tsx`
- `app/models/mission_control.py`
- `app/services/mission_control_service.py`
- `app/api/mission_control.py`

Create:
- `apps/mission-control/src/components/OrgSwitcher.tsx`
- `apps/mission-control/src/components/AgentReleasePanel.tsx`
- `apps/mission-control/src/components/SkillBindingsPanel.tsx`
- `apps/mission-control/src/components/HostAdapterBadge.tsx`
- `apps/mission-control/src/components/SecretHealthPanel.tsx`
- `apps/mission-control/src/components/AuditTimeline.tsx`
- `apps/mission-control/src/components/UsageSummaryCard.tsx`
- `apps/mission-control/src/pages/AgentDetailPage.tsx`
- `apps/mission-control/src/pages/UsagePage.tsx`
- `apps/mission-control/src/pages/AuditPage.tsx`
- `apps/mission-control/src/pages/SecretsPage.tsx`
- `apps/mission-control/src/pages/AgentDetailPage.test.tsx`
- `apps/mission-control/src/pages/UsagePage.test.tsx`
- `apps/mission-control/src/pages/AuditPage.test.tsx`
- `apps/mission-control/src/components/AgentReleasePanel.test.tsx`

### Tasks

1. Reorder the internal information architecture.
   - Make agents a first-class navigation surface, not a secondary widget under a generic app shell.
   - Keep dashboard, inbox, approvals, and runs as operator views around agents.

2. Add the internal agent lifecycle workflow.
   - Create agent
   - bind skills
   - select host adapter
   - bind secrets/assets
   - publish candidate revision
   - run/test it
   - inspect audit/usage/outcomes
   - rollback if needed

3. Surface host-adapter visibility.
   - Show which host adapter a revision uses.
   - Show compatibility warnings when an agent references a disabled adapter.
   - Show Trigger-specific runtime details as adapter details, not as platform identity.

4. Add governance surfaces.
   - Secrets health
   - audit timeline
   - usage summary
   - release status and rollback controls

5. Keep backend ownership of read models.
   - The UI should render typed backend responses, not invent new frontend-only truth models.
   - Continue avoiding business logic in the frontend.

### Tests / Verification

Run:
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest tests/api/test_mission_control.py -q`
- `uv run pytest -q`

Add explicit assertions for:
- agents appearing as the main working surface
- agent detail view showing revision, skills, host, secrets health, audit, and usage
- rollback and publish actions rendering only when RBAC allows them

### Documentation Updates

Modify:
- `README.md`
- `docs/superpowers/specs/2026-04-13-hermes-mission-control-ui-design.md`
- `docs/mission-control-wiki/concepts/agentic-first-command-center.md`
- `docs/mission-control-wiki/index.md`

Document:
- Mission Control as the dogfood cockpit for the agent platform
- agents as the primary unit of work in the UI
- governance panels and release supervision

### Exit Gate

Before continuing, an internal operator should be able to complete the end-to-end agent lifecycle from Mission Control without touching raw database state.

---

## Phase 6 — Add internal catalog first, then marketplace distribution

### Goal

Add distribution without changing the core execution model: first as an internal private catalog, then as a marketplace-ready install flow.

### Files

Modify:
- `app/models/agents.py`
- `app/services/agent_registry_service.py`
- `app/api/agents.py`
- `app/main.py`
- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/lib/api.ts`

Create:
- `supabase/migrations/202604150005_agent_catalog_and_marketplace.sql`
- `app/models/catalog.py`
- `app/models/agent_installs.py`
- `app/db/catalog.py`
- `app/db/agent_installs.py`
- `app/services/catalog_service.py`
- `app/services/agent_install_service.py`
- `app/api/catalog.py`
- `app/api/agent_installs.py`
- `apps/mission-control/src/pages/CatalogPage.tsx`
- `apps/mission-control/src/components/AgentInstallWizard.tsx`
- `apps/mission-control/src/pages/CatalogPage.test.tsx`
- `tests/db/test_catalog_repository.py`
- `tests/db/test_agent_install_repository.py`
- `tests/api/test_catalog.py`
- `tests/api/test_agent_installs.py`

### Tasks

1. Add internal catalog metadata.
   - Catalog entries should point at agent revisions, not apps.
   - Include host compatibility, required skills, required secret bindings, release channel, and install instructions.

2. Add install flows.
   - Installing a catalog entry should create an org-scoped installed agent record or cloned revision, depending on the chosen isolation model.
   - Preserve source revision lineage and compatibility data.

3. Add marketplace readiness controls.
   - Support visibility states such as `internal`, `private_catalog`, `marketplace_candidate`, and `marketplace_published`.
   - Require enterprise controls and release checks before a listing can move beyond internal catalog.

4. Preserve host portability.
   - Catalog metadata must declare compatible host adapters.
   - Installing a Trigger-only agent into a Codex-only environment should fail clearly before runtime.

5. Keep marketplace behind a feature flag until dogfood data says it is safe.
   - Internal catalog can ship first.
   - Public or partner marketplace should remain disabled by default.

### Tests / Verification

Run:
- `uv run pytest tests/db/test_catalog_repository.py -q`
- `uv run pytest tests/db/test_agent_install_repository.py -q`
- `uv run pytest tests/api/test_catalog.py -q`
- `uv run pytest tests/api/test_agent_installs.py -q`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `uv run pytest -q`

Add explicit assertions for:
- internal catalog listings referencing agent revisions, not apps
- install compatibility checks enforcing host and secret requirements
- installed agents retaining rollback and audit behavior
- marketplace flags preventing accidental public release

### Documentation Updates

Modify:
- `README.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-15-agent-platform-product-model.md`
- `docs/mission-control-wiki/concepts/agent-platform-product-model.md`

Create:
- `docs/superpowers/specs/2026-04-15-agent-marketplace-distribution.md`
- `docs/mission-control-wiki/concepts/agent-marketplace-model.md`

Document:
- internal catalog first rollout
- install and compatibility rules
- marketplace readiness checklist

### Exit Gate

Marketplace distribution cannot move forward until internal catalog installs are stable and enterprise controls are enforced in staging.

---

## Cross-Phase Implementation Rules

### 1. Migration rules

- Never rewrite `supabase/migrations/202604130001_hermes_control_plane_core.sql`.
- Do not depend on editing already-applied migrations.
- Treat `supabase/migrations/202604130003_mission_control_managed_agents.sql` as historical scaffold and supersede with new additive migration files.
- Every new table must carry enough correlation fields for org, agent, revision, session, and run tracing.

### 2. Adapter rules

- All runtime dispatch must go through `app/services/agent_execution_service.py` and the `app/host_adapters/` registry.
- Trigger.dev-specific fields belong under the Trigger adapter or Trigger callback contract, not under generic agent identity fields.
- Codex and Anthropic runtimes should be added as adapter implementations, not as forks of agent logic.

### 3. Product rules

- Do not add a new `apps/<agent-name>/` surface for each agent.
- Agents are records and revisions in the platform, surfaced through Mission Control and catalog APIs.
- Skills remain reusable and composable across many agents.

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

## Definition of Done

This plan is complete when Ares can truthfully say:
- agents are the primary product unit
- Mission Control is the internal operator cockpit, not the product boundary
- Trigger.dev is an adapter, not the platform identity
- org tenancy, RBAC, secrets, audit, usage, replay, and rollback are first-class
- agent revisions can be published, supervised, replayed, and rolled back safely
- skills are reusable across agents
- Codex and Anthropic runtimes have a preserved adapter seam even if not yet enabled
- internal catalog distribution works before marketplace exposure
