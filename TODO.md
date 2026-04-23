---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-23T00:24:46Z"
repo: "martinp09/Ares"
local_checkout: "/root/.config/superpowers/worktrees/Hermes-Central-Command/mission-control-enterprise-backlog"
current_branch: "feature/mission-control-enterprise-backlog"
---

# Ares TODO / Handoff

## Canonical branch docs

- Master scope: `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md`
- Active slice order: `docs/superpowers/plans/2026-04-22-mission-control-enterprise-backlog-sliced-execution-plan.md`
- Live source input: `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- Live source input: `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- Runtime boundary notes: `docs/hermes-ares-integration-runbook.md`

## Hard rules for the next session

1. Reconstruct from git + repo files only.
2. Do **not** touch Supabase in this environment.
3. Preserve existing non-Supabase wiring.
4. Keep `business_id + environment` alive while adding/using `org_id`.
5. Keep changes additive and bounded by slice.
6. Do not claim a slice is good without tests **and** QC approval.

## Completed slices before this handoff

- Phase 2 complete and QC-approved.
- Phase 3 complete through `P3.5` and QC-approved on the active non-Supabase path.
- Phase 4 complete through `P4.5` and QC-approved.
- Phase 5 complete through `P5.5` on the active non-Supabase path.
- Phase 6 `P6.1` complete and QC-approved.

## Current slice

## P6.2 — First bounded agent-detail workflow

### Goal of this slice

Add the first **read-only** Mission Control agent-detail experience without touching Supabase:
- open an agent detail page from the agents workspace
- show lifecycle/read-model detail only
- no publish / rollback / mutation controls yet
- keep the rest of Mission Control as adjacent operator surfaces

### Files already changed in this slice

- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/App.test.tsx`
- `apps/mission-control/src/components/AgentRegistryTable.tsx`
- `apps/mission-control/src/lib/api.ts`
- `apps/mission-control/src/lib/api.test.ts`
- `apps/mission-control/src/lib/fixtures.ts`
- `apps/mission-control/src/pages/AgentsPage.tsx`
- `apps/mission-control/src/pages/AgentsPage.test.tsx`
- `apps/mission-control/src/pages/AgentDetailPage.tsx`
- `apps/mission-control/src/pages/AgentDetailPage.test.tsx`

### What is already working

- Agents workspace can open a dedicated `AgentDetailPage`.
- The page is read-only and intentionally does not expose publish/rollback controls.
- The detail page renders:
  - current posture
  - revision history
  - release history / latest release posture
  - secrets health
  - recent audit
  - usage summary / recent usage
  - recent turns
- Partial auxiliary endpoint failures now degrade sections explicitly instead of blindly fabricating success or empty-state truth.
- Latest release posture is derived from event timestamps rather than trusting array position.
- Search exclusion clears hidden selected agents.
- The agents surface now has its own retry path after fallback.

### Latest verification evidence

Frontend:
- `npm --prefix apps/mission-control run test -- --run` → `22 passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass

Backend targeted:
- `./.venv/bin/python -m pytest tests/api/test_mission_control.py tests/api/test_agents.py tests/api/test_release_management.py -q` → `40 passed`

Backend full suite:
- `./.venv/bin/python -m pytest -q` → `452 passed, 5 warnings`

Known warnings:
- existing `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warnings in older tests

## Why P6.2 is **not** done / why QC would not sign off

P6.2 is **implemented but not QC-approved**. The blockers are all about truthfulness and transient-state correctness, not missing broad functionality.

### Blocker 1 — stale context panel during agent-to-agent switches

The main pane has a stronger render guard than the side context panel.

Current seam:
- `apps/mission-control/src/App.tsx`
- main detail rendering is guarded by `canRenderSelectedAgentDetail`
- the side `ContextPanel` still derives items from `selectedAgentDetail` without an equally strict id-match/loading gate during fast transitions

Meaning:
- when switching from one visible agent to another, the main pane can correctly show loading while the side panel can still describe old agent detail

What to do:
- make the side panel use the same truth gate as the main detail pane
- safest fix: if detail is loading or `selectedAgentDetail.agent.id !== selectedAgentId`, render neutral/loading context rather than stale counts
- add a focused App test for visible agent A → visible agent B switching while detail is in-flight

### Blocker 2 — degraded root-detail fallback still drops known summary identity fields

The backend summary contract already carries more truth than the degraded fallback uses.

Current seam:
- backend summary exposes `business_id` / `description`
- frontend `AgentSummary` mapper in `apps/mission-control/src/lib/api.ts` still drops those fields from summary state
- degraded fallback in `apps/mission-control/src/App.tsx` still has to fabricate placeholders like unavailable/unknown where summary truth should survive

Meaning:
- if `/agents/{id}` detail fails but the agent summary is live, the fallback can present weaker identity/business truth than the UI actually already knows

What to do:
- extend frontend `AgentSummary` to preserve summary-level identity fields already present in the backend contract
- update `mapAgents(...)` in `apps/mission-control/src/lib/api.ts`
- update degraded root-detail fallback in `apps/mission-control/src/App.tsx` to reuse those fields instead of placeholder garbage
- update fixture/test payloads so this path is covered explicitly

### Blocker 3 — shell-level fallback/source labels can lag after agents recover

The agents page can recover to live data while shell chrome still reports stale fallback posture.

Current seam:
- `apps/mission-control/src/App.tsx`
- agents-only retry updates `snapshot.agents` and `agentsDataSource`
- outer shell badge/footer still derive from broader `dataSource` / `fallbackViews`

Meaning:
- page-level surface can say one thing while shell badge/footer imply fallback mode from an earlier failure

What to do:
- reconcile shell-level source state after agents recovery
- either recompute shell-level source/fallback state when the retry succeeds, or separate shell labels so they do not overstate fallback after local recovery
- add an App test for: initial `/mission-control/agents` fallback → later successful agents retry → shell and agents surface agree

## Smallest safe next steps for the next session

1. Fix **context panel stale-detail gating** in `apps/mission-control/src/App.tsx`.
2. Extend frontend **AgentSummary** shape and mapper to preserve summary identity fields in `apps/mission-control/src/lib/api.ts`.
3. Reuse preserved summary truth in degraded fallback inside `apps/mission-control/src/App.tsx`.
4. Reconcile shell-level `statusBadge` / `footerNote` with recovered agents source state in `apps/mission-control/src/App.tsx`.
5. Add focused regressions in:
   - `apps/mission-control/src/App.test.tsx`
   - `apps/mission-control/src/lib/api.test.ts`
6. Re-run full verification.
7. Run fresh XHIGH QC before calling `P6.2` done.

## Exit gate for P6.2

Do **not** close `P6.2` until all are true:
- side context panel cannot show stale detail during agent switches
- degraded detail preserves summary identity/business truth when available
- shell/source labels stay truthful after agents retry recovery
- frontend tests pass
- frontend typecheck passes
- frontend build passes
- targeted backend tests pass
- full backend suite passes
- QC returns non-blocker / approved

## Repo cleanup check already performed

- Searched for stray spec/plan files.
- No obviously foreign plan/spec files were found that clearly do not belong in this repo.
- No plan/spec files were deleted in this handoff prep because there was nothing high-confidence to remove without being reckless.
