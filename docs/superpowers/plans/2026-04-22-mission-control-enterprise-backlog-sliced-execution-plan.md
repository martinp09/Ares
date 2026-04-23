# Mission Control Enterprise Backlog Sliced Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `software-development/subagent-driven-development` plus `software-development/phase-swarm-qc-orchestration` for implementation and review. Keep steps slice-sized, use fresh subagents, and do not close a slice without verification.

**Goal:** Finish the remaining Mission Control + enterprise backlog with small, independently verifiable slices.

**Architecture:** Build on the current in-memory/app-layer baseline. Preserve the current control-plane/runtime seams, keep `business_id + environment` alive while using `org_id` as the enterprise parent scope, and explicitly defer all Supabase backend wiring in this environment.

**Tech Stack:** FastAPI, in-memory control-plane repositories, pytest, React/Vite Mission Control UI, Trigger.dev adapter seam, Codex subagents for implementation, XHIGH QC review.

---

## Hard rules for this plan

- **Forbidden in this environment:** `supabase/`, migrations, database rewiring, `control_plane_store_supabase` changes, or any backend persistence cutover.
- Keep all changes **additive** and **in-memory/app-layer/UI-layer**.
- Close work by **slice**, not by giant phase blob.
- Every slice must end with:
  - targeted tests
  - full `./.venv/bin/python -m pytest -q`
  - XHIGH QC review before claiming the slice or phase is good
- Do not let a later slice bleed into the current slice unless a blocker forces it.

---

## Phase 2 close — Org tenancy and actor context

### Slice P2.0 — Final QC signoff

**Files:**
- Review only current Phase 2 diff

- [ ] **Step 1: Run full backend tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```
Expected: all tests pass.

- [ ] **Step 2: Run XHIGH QC review**

Review scope:
- org/membership APIs
- agent/session/permission/RBAC org scoping
- Mission Control org isolation

Expected: no remaining org-leak or forbidden-Supabase findings.

- [ ] **Step 3: If QC finds issues, fix only the flagged files**

Allowed fix scope:
- current Phase 2 files only

- [ ] **Step 4: Re-run tests after fixes**

Run:
```bash
./.venv/bin/python -m pytest -q
```
Expected: all tests pass again.

**Exit gate:**
- Phase 2 has a clean QC approval and full test pass.

---

## Phase 3 — Agents as deployable units + host-adapter contract

### Slice P3.1 — Product-shape the agent and revision records

**Files:**
- Modify: `app/models/agents.py`
- Modify: `app/db/agents.py`
- Modify: `app/services/agent_registry_service.py`
- Modify: `app/api/agents.py`
- Test: `tests/api/test_agents.py`

- [ ] **Step 1: Add product metadata to agent records**

Add fields for:
- `slug`
- `visibility`
- `lifecycle_status`
- `packaging_metadata`

- [ ] **Step 2: Add richer revision metadata**

Add fields for:
- `input_schema`
- `output_schema`
- `release_notes`
- `compatibility_metadata`

- [ ] **Step 3: Keep current scope fields intact**

Preserve:
- `org_id`
- `business_id`
- `environment`

- [ ] **Step 4: Add/update agent API tests**

Test for:
- new metadata round-trip
- no regression in create/publish/archive/clone

- [ ] **Step 5: Run targeted tests**

Run:
```bash
./.venv/bin/python -m pytest tests/api/test_agents.py -q
```

- [ ] **Step 6: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- agents and revisions look like real product/runtime units, not just scaffolds.

---

### Slice P3.2 — Finish the skill registry contract

**Files:**
- Modify: `app/models/skills.py`
- Modify: `app/db/skills.py`
- Modify: `app/services/skill_registry_service.py`
- Modify: `app/api/skills.py`
- Test: `tests/db/test_skills_repository.py`
- Test: `tests/api/test_skills.py`

- [ ] **Step 1: Add explicit skill metadata**

Support:
- name
- description
- required tools
- permission requirements
- input/output contract metadata

- [ ] **Step 2: Validate skill references from agent revisions**

Ensure invalid skill IDs fail cleanly.

- [ ] **Step 3: Keep skills reusable across many agents**

No agent-specific embedding hacks.

- [ ] **Step 4: Run targeted skill tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_skills_repository.py tests/api/test_skills.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- skills are first-class reusable procedures with stable validation.

---

### Slice P3.3 — Harden the host-adapter contract

**Files:**
- Modify: `app/models/host_adapters.py`
- Modify: `app/host_adapters/base.py`
- Modify: `app/host_adapters/registry.py`
- Modify: `app/host_adapters/trigger_dev.py`
- Modify: `app/host_adapters/codex.py`
- Modify: `app/host_adapters/anthropic.py`
- Test: `tests/host_adapters/test_host_registry.py`
- Test: `tests/host_adapters/test_trigger_dev_adapter.py`
- Test: `tests/host_adapters/test_disabled_host_adapters.py`

- [ ] **Step 1: Make the adapter interface explicit**

Cover:
- dispatch
- status correlation
- artifact reporting
- cancellation / disabled behavior

- [ ] **Step 2: Keep Codex and Anthropic registered but disabled**

Do not fake-enable them.

- [ ] **Step 3: Add compatibility/read-model fields needed later by UI**

- [ ] **Step 4: Run adapter tests**

Run:
```bash
./.venv/bin/python -m pytest tests/host_adapters/test_host_registry.py tests/host_adapters/test_trigger_dev_adapter.py tests/host_adapters/test_disabled_host_adapters.py -q
```

- [ ] **Step 5: Run Trigger typecheck**

Run:
```bash
npx tsc -p trigger/tsconfig.json --noEmit
```

- [ ] **Step 6: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- adapter registry is the canonical execution seam.

---

### Slice P3.4 — Enforce execution-through-adapter

**Files:**
- Modify: `app/services/agent_execution_service.py`
- Modify: `app/services/run_service.py`
- Modify: `app/services/command_service.py`
- Modify: `app/services/session_service.py` if needed
- Test: `tests/services/test_agent_execution_service.py`
- Test: `tests/api/test_agents.py`

- [ ] **Step 1: Verify all runtime dispatch paths go through `agent_execution_service`**
- [ ] **Step 2: Remove any remaining direct Trigger assumptions in runtime services**
- [ ] **Step 3: Preserve run correlation IDs and session pinning**
- [ ] **Step 4: Run targeted execution tests**

Run:
```bash
./.venv/bin/python -m pytest tests/services/test_agent_execution_service.py tests/api/test_agents.py -q
```

- [ ] **Step 5: Run full tests + trigger typecheck**

Run:
```bash
npx tsc -p trigger/tsconfig.json --noEmit
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- runtime -> adapter registry -> adapter is the only execution path.

---

### Slice P3.5 — Make Hermes tools data-backed

**Files:**
- Modify: `app/services/hermes_tools_service.py`
- Modify: `app/api/hermes_tools.py` if needed
- Test: `tests/api/test_hermes_tools.py`
- Test: permission/RBAC tests if affected

- [ ] **Step 1: Derive tool visibility from skills + revision policy**
- [ ] **Step 2: Keep backward compatibility for existing command types**
- [ ] **Step 3: Preserve permission/RBAC enforcement**
- [ ] **Step 4: Run targeted tests**

Run:
```bash
./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_permissions.py tests/api/test_rbac.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Phase 3 exit gate:**
- an agent revision is the executable unit, host selection is explicit, skill binding is first-class, and runtime dispatch is adapter-driven.

---

## Phase 4 — Enterprise controls

### Slice P4.1 — Finish RBAC role model

**Files:**
- Modify: `app/models/rbac.py`
- Modify: `app/db/rbac.py`
- Modify: `app/services/rbac_service.py`
- Modify: `app/api/rbac.py`
- Test: `tests/db/test_rbac_repository.py`
- Test: `tests/api/test_rbac.py`

- [ ] **Step 1: Normalize/complete role set**

Support:
- `platform_admin`
- `org_admin`
- `agent_builder`
- `operator`
- `reviewer`
- `auditor`

- [ ] **Step 2: Make effective permission resolution deterministic**
- [ ] **Step 3: Add blocked-action negative tests**
- [ ] **Step 4: Run targeted RBAC tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- role-based access is predictable, complete, and test-covered.

---

### Slice P4.2 — Finish secrets resource model

**Files:**
- Modify: `app/models/secrets.py`
- Modify: `app/db/secrets.py`
- Modify: `app/services/secrets_service.py`
- Modify: `app/api/secrets.py`
- Test: `tests/db/test_secrets_repository.py`
- Test: `tests/api/test_secrets.py`

- [ ] **Step 1: Separate secret metadata from values**
- [ ] **Step 2: Bind revisions to named secret refs only**
- [ ] **Step 3: Enforce redaction everywhere**
- [ ] **Step 4: Ensure secret reads/updates emit audit events**
- [ ] **Step 5: Run targeted secret tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_secrets_repository.py tests/api/test_secrets.py -q
```

- [ ] **Step 6: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- secrets never leak raw plaintext through the API layer.

---

### Slice P4.3 — Finish append-only audit model

**Files:**
- Modify: `app/models/audit.py`
- Modify: `app/db/audit.py`
- Modify: `app/services/audit_service.py`
- Modify: `app/api/audit.py`
- Test: `tests/db/test_audit_repository.py`
- Test: `tests/api/test_audit.py`

- [ ] **Step 1: Make append-only behavior explicit**
- [ ] **Step 2: Ensure correlation fields are complete**
- [ ] **Step 3: Expand audit coverage for critical runtime actions**
- [ ] **Step 4: Run targeted audit tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_audit_repository.py tests/api/test_audit.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- audit log is append-only, correlated, and trustworthy.

---

### Slice P4.4 — Finish usage accounting

**Files:**
- Modify: `app/models/usage.py`
- Modify: `app/db/usage.py`
- Modify: `app/services/usage_service.py`
- Modify: `app/api/usage.py`
- Test: `tests/db/test_usage_repository.py`
- Test: `tests/api/test_usage.py`

- [ ] **Step 1: Track usage per org/agent/revision/run/tool invocation**
- [ ] **Step 2: Keep the usage model adapter-agnostic**
- [ ] **Step 3: Add aggregation tests across more than one adapter kind**
- [ ] **Step 4: Run targeted usage tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_usage_repository.py tests/api/test_usage.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- usage accounting is adapter-agnostic and operator-usable.

---

### Slice P4.5 — Surface governance in Mission Control

**Files:**
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `apps/mission-control/src/pages/SettingsPage.tsx`
- Test: `tests/api/test_mission_control.py`

- [ ] **Step 1: Add backend read models for secrets health, audit, usage, approvals**
- [ ] **Step 2: Render those views in Settings / governance surfaces**
- [ ] **Step 3: Keep frontend backend-driven only**
- [ ] **Step 4: Run UI tests/typecheck/build + targeted backend tests**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
./.venv/bin/python -m pytest tests/api/test_mission_control.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Phase 4 exit gate:**
- internal operator workflows can inspect and trust roles, secrets, audit, usage, and governance from Mission Control.

---

## Phase 5 — Release lifecycle, replay, evaluation, rollback

### Slice P5.1 — Expand revision lifecycle states

**Files:**
- Modify: `app/models/agents.py`
- Modify: `app/db/agents.py`
- Modify: `app/services/agent_registry_service.py`
- Test: `tests/api/test_agents.py`

- [ ] **Step 1: Add richer revision states**

Support:
- `draft`
- `candidate`
- `published`
- `deprecated`
- `archived`
- `rolled_back` or equivalent release-event semantics

- [ ] **Step 2: Add release channel metadata**
- [ ] **Step 3: Add tests for state transitions**
- [ ] **Step 4: Run targeted agent tests**

Run:
```bash
./.venv/bin/python -m pytest tests/api/test_agents.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- revision lifecycle is richer than draft/published/archive.

---

### Slice P5.2 — Add release-management domain

**Files:**
- Create: `app/models/release_management.py`
- Create: `app/db/release_management.py`
- Create: `app/services/release_management_service.py`
- Create: `app/api/release_management.py`
- Modify: `app/main.py`
- Test: `tests/db/test_release_management_repository.py`
- Test: `tests/api/test_release_management.py`

- [ ] **Step 1: Add release event records**
- [ ] **Step 2: Add active revision pointer transitions**
- [ ] **Step 3: Add rollback event model without rewriting history**
- [ ] **Step 4: Run targeted release-management tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_release_management_repository.py tests/api/test_release_management.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- release actions are runtime-owned and immutable-history-safe.

---

### Slice P5.3 — Upgrade replay lineage

**Files:**
- Modify: `app/services/replay_service.py`
- Modify: `app/services/run_lifecycle_service.py`
- Modify: `app/models/runs.py`
- Modify: `app/api/replays.py`
- Test: `tests/api/test_replays.py`

- [ ] **Step 1: Add revision/release context to replay lineage**
- [ ] **Step 2: Add triggering actor info**
- [ ] **Step 3: Preserve parent-child lineage cleanly**
- [ ] **Step 4: Run targeted replay tests**

Run:
```bash
./.venv/bin/python -m pytest tests/api/test_replays.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- replay lineage is revision-aware and runtime-owned.

---

### Slice P5.4 — Tie outcomes/evals to promotion and rollback

**Files:**
- Modify: `app/models/outcomes.py`
- Modify: `app/services/outcome_service.py`
- Modify: release-management service/tests
- Test: `tests/api/test_outcomes.py`

- [ ] **Step 1: Add evaluation summaries for release decisions**
- [ ] **Step 2: Let failed evals block promotion when required**
- [ ] **Step 3: Attach rollback reasoning to outcomes where relevant**
- [ ] **Step 4: Run targeted outcomes/release tests**

Run:
```bash
./.venv/bin/python -m pytest tests/api/test_outcomes.py tests/api/test_release_management.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Exit gate:**
- release decisions can be policy-gated by outcomes/evaluations.

---

### Slice P5.5 — Add release read models in Mission Control

**Files:**
- Modify: `app/models/mission_control.py`
- Modify: `app/services/mission_control_service.py`
- Modify: `app/api/mission_control.py`
- Modify: `apps/mission-control/src/pages/AgentsPage.tsx`
- Modify: `apps/mission-control/src/pages/RunsPage.tsx`
- Test: `tests/api/test_mission_control.py`

- [ ] **Step 1: Expose release/replay/rollback/eval state in read models**
- [ ] **Step 2: Render that state in Agents/Runs views**
- [ ] **Step 3: Run UI/backend targeted verification**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
./.venv/bin/python -m pytest tests/api/test_mission_control.py -q
```

- [ ] **Step 4: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Phase 5 exit gate:**
- a revision can be promoted, replayed, evaluated, observed, and rolled back with runtime-owned lineage.

---

## Phase 6 — Productize Mission Control for operator workflow

### Slice P6.1 — Rework navigation so agents are central

**Files:**
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/components/MissionControlShell.tsx`
- Modify: `apps/mission-control/src/pages/AgentsPage.tsx`

- [ ] **Step 1: Make agents a first-class nav/work surface**
- [ ] **Step 2: Keep dashboard/inbox/approvals/runs as operator views around agents**
- [ ] **Step 3: Run UI tests/typecheck/build**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

**Exit gate:**
- information architecture matches the product model.

---

### Slice P6.2 — Add the agent detail workflow

**Files:**
- Create: `apps/mission-control/src/pages/AgentDetailPage.tsx`
- Create: `apps/mission-control/src/pages/AgentDetailPage.test.tsx`
- Modify: backend mission-control read models if needed

- [ ] **Step 1: Show revision list, skills, adapter, secrets health, audit, usage, release controls**
- [ ] **Step 2: Keep UI driven by typed backend responses**
- [ ] **Step 3: Run UI/backend targeted verification**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
./.venv/bin/python -m pytest tests/api/test_mission_control.py -q
```

**Exit gate:**
- one page shows the real lifecycle of an agent.

---

### Slice P6.3 — Add release panels and host visibility

**Files:**
- Create: `apps/mission-control/src/components/AgentReleasePanel.tsx`
- Create: `apps/mission-control/src/components/HostAdapterBadge.tsx`
- Modify: `apps/mission-control/src/pages/AgentsPage.tsx`
- Modify: `apps/mission-control/src/pages/RunsPage.tsx`
- Create tests

- [ ] **Step 1: Render publish/rollback controls appropriately**
- [ ] **Step 2: Show active/disabled adapter state and compatibility warnings**
- [ ] **Step 3: Keep Trigger details labeled as adapter details**
- [ ] **Step 4: Run UI verification**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

**Exit gate:**
- release and adapter status are operator-visible.

---

### Slice P6.4 — Add governance surfaces

**Files:**
- Create: `apps/mission-control/src/pages/SecretsPage.tsx`
- Create: `apps/mission-control/src/pages/AuditPage.tsx`
- Create: `apps/mission-control/src/pages/UsagePage.tsx`
- Create: `apps/mission-control/src/components/SecretHealthPanel.tsx`
- Create: `apps/mission-control/src/components/AuditTimeline.tsx`
- Create: `apps/mission-control/src/components/UsageSummaryCard.tsx`
- Create tests

- [ ] **Step 1: Surface secrets health**
- [ ] **Step 2: Surface audit timeline**
- [ ] **Step 3: Surface usage summaries**
- [ ] **Step 4: Run UI/backend targeted verification**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
./.venv/bin/python -m pytest tests/api/test_mission_control.py -q
```

**Exit gate:**
- governance is usable from Mission Control, not hidden in raw APIs.

---

### Slice P6.5 — Add org-aware navigation/filtering

**Files:**
- Create: `apps/mission-control/src/components/OrgSwitcher.tsx`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/api.ts`
- Modify: backend mission-control read models if needed

- [ ] **Step 1: Add org switcher**
- [ ] **Step 2: Preserve business/environment as secondary filters**
- [ ] **Step 3: Keep backend as source of truth**
- [ ] **Step 4: Run UI/backend targeted verification**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
./.venv/bin/python -m pytest tests/api/test_mission_control.py -q
```

- [ ] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Phase 6 exit gate:**
- an internal operator can manage the end-to-end agent lifecycle from Mission Control without raw database state.

---

## Phase 7 — Internal catalog first, marketplace later

### Slice P7.1 — Add the catalog domain

**Status note (2026-04-23):** backend/domain portion implemented and verified on the active branch. Mission Control UI work remains in `P7.2`.

**Files:**
- Create: `app/models/catalog.py`
- Create: `app/models/agent_installs.py`
- Create: `app/db/catalog.py`
- Create: `app/db/agent_installs.py`
- Create: `app/services/catalog_service.py`
- Create: `app/services/agent_install_service.py`
- Create: `app/api/catalog.py`
- Create: `app/api/agent_installs.py`
- Modify: `app/main.py`
- Modify: `app/db/client.py`
- Test: `tests/db/test_catalog_repository.py`
- Test: `tests/db/test_agent_install_repository.py`
- Test: `tests/api/test_catalog.py`
- Test: `tests/api/test_agent_installs.py`

- [x] **Step 1: Add catalog entries that point at agent revisions**
- [x] **Step 2: Add host/skill/secret/release compatibility metadata**
- [x] **Step 3: Add install record model and lineage preservation**
- [x] **Step 4: Run targeted catalog/install tests**

Run:
```bash
./.venv/bin/python -m pytest tests/db/test_catalog_repository.py tests/db/test_agent_install_repository.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/api/test_agents.py -q
```

- [x] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Verification snapshot (2026-04-23):**
- `./.venv/bin/python -m pytest tests/db/test_catalog_repository.py tests/db/test_agent_install_repository.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` → `21 passed`
- `./.venv/bin/python -m pytest -q` → `460 passed, 5 warnings`

**Exit gate:**
- catalog and install domain exists without changing execution semantics.

---

### Slice P7.2 — Add catalog UI

**Status note (2026-04-23):** implemented and verified on the active branch. The catalog UI now stays org-scoped, shows compatibility requirements before install, disables installs while the catalog is fixture-backed, and drops stale install/catalog writes across scope changes.

**Files:**
- Create: `apps/mission-control/src/pages/CatalogPage.tsx`
- Create: `apps/mission-control/src/components/AgentInstallWizard.tsx`
- Create: `apps/mission-control/src/pages/CatalogPage.test.tsx`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/api.ts`

- [x] **Step 1: Add catalog browse/install UX**
- [x] **Step 2: Show compatibility requirements before install**
- [x] **Step 3: Show install failure reasons before runtime**
- [x] **Step 4: Run UI verification**

Run:
```bash
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

**Verification snapshot (2026-04-23):**
- `npm --prefix apps/mission-control run test -- --run src/App.test.tsx src/lib/api.test.ts src/pages/CatalogPage.test.tsx` → `31 passed`
- `npm --prefix apps/mission-control run test -- --run` → `20 files passed`, `58 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass
- `./.venv/bin/python -m pytest -q` → `465 passed, 5 warnings`

**Exit gate:**
- internal catalog is usable end-to-end.

---

### Slice P7.3 — Add marketplace readiness flags (not public launch)

**Status note (2026-04-23):** implemented and verified on the active branch. Catalog/agent visibility now supports `internal`, `private_catalog`, and `marketplace_candidate` as internal metadata, while `marketplace_published` is fail-closed behind an explicit config gate so public launch stays disabled by default.

**Files:**
- Modify: `app/models/agents.py`
- Modify: catalog services/APIs
- Modify: catalog UI badges if needed
- Test: catalog/install tests

- [x] **Step 1: Add visibility states**

Support:
- `internal`
- `private_catalog`
- `marketplace_candidate`
- `marketplace_published`

- [x] **Step 2: Keep external/public release disabled by default**
- [x] **Step 3: Add tests for accidental public-release prevention**
- [x] **Step 4: Run targeted + UI verification**

Run:
```bash
./.venv/bin/python -m pytest tests/api/test_catalog.py tests/api/test_agent_installs.py -q
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

**Verification snapshot (2026-04-23):**
- `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/api/test_agent_installs.py -q` → `6 passed`
- `npm --prefix apps/mission-control run test -- --run` → `20 files passed`, `59 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass
- QC fix follow-up:
  - `npm --prefix apps/mission-control run test -- --run src/App.test.tsx src/pages/CatalogPage.test.tsx src/lib/api.test.ts` → `32 passed`
  - `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/db/test_catalog_repository.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` → `24 passed`

- [x] **Step 5: Run full tests**

Run:
```bash
./.venv/bin/python -m pytest -q
```

**Phase 7 verification snapshot (2026-04-23):**
- `./.venv/bin/python -m pytest -q` → `469 passed, 5 warnings`

**Phase 7 exit gate:**
- internal catalog works, marketplace remains controlled metadata only, and no public launch is implied.

---

## Recommended execution order

1. P2.0 final QC signoff
2. P3.1 product-shaped agent metadata
3. P3.2 skill registry hardening
4. P3.3 host-adapter contract hardening
5. P3.4 execution-through-adapter enforcement
6. P3.5 data-backed Hermes tools
7. P4.1 RBAC completion
8. P4.2 secrets hardening
9. P4.3 audit completion
10. P4.4 usage completion
11. P4.5 governance surfaces
12. P5.1 revision states
13. P5.2 release-management domain
14. P5.3 replay lineage
15. P5.4 eval-gated promotion / rollback
16. P5.5 Mission Control release read models
17. P6.1 IA/nav rework
18. P6.2 agent detail page
19. P6.3 release panels + host visibility
20. P6.4 governance pages
21. P6.5 org switcher / org-aware nav
22. P7.1 catalog domain
23. P7.2 catalog UI
24. P7.3 marketplace readiness flags

## Completion standard

Do not call a slice or phase done until:
- targeted tests pass
- full `./.venv/bin/python -m pytest -q` passes
- UI/TS checks pass when the slice touches frontend/Trigger
- XHIGH QC approves the slice
