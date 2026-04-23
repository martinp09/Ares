---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-23T03:07:06Z"
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
- Phase 6 complete through `P6.5` and QC-approved.

## Current status

There is no active Phase 6 slice anymore. `P6.1` through `P6.5` are closed on this branch.

### Phase 6 final closeout

- `P6.3` added release/host visibility to the Mission Control shell through the agents-first workflow.
- `P6.4` added read-only governance surfaces for secrets health, audit, usage, and settings.
- `P6.5` added org-aware navigation/filtering while keeping `business_id + environment` alive as secondary scope and preserving the non-Supabase path.

### Final P6.5 blocker fixes landed

1. Prior-scope detail now stays neutral during org/business/environment and conversation switches instead of rendering stale inbox or agent detail while reloads are in flight.
2. Fallback rendering now respects secondary business/environment filters without leaking unscoped fixture agents/runs.
3. Org-only fixture fallback now fails neutral for dashboard/inbox/tasks/approvals/settings surfaces instead of relabeling internal fixture truth under another org.
4. Settings assets now re-fetch on `business_id` / `environment` changes because the cache key matches the scoped request contract.

### Files changed across the final Phase 6 slices

- Backend:
  - `app/services/organization_service.py`
  - `app/models/mission_control.py`
  - `app/services/mission_control_service.py`
  - `tests/api/test_mission_control.py`
  - `tests/api/test_organizations.py`
  - `tests/services/test_mission_control_service.py`
- Frontend:
  - `apps/mission-control/src/App.tsx`
  - `apps/mission-control/src/App.test.tsx`
  - `apps/mission-control/src/lib/api.ts`
  - `apps/mission-control/src/lib/api.test.ts`
  - `apps/mission-control/src/components/MissionControlShell.tsx`
  - `apps/mission-control/src/components/MissionControlShell.test.tsx`
  - `apps/mission-control/src/components/OrgSwitcher.tsx`
  - `apps/mission-control/src/components/OrgSwitcher.test.tsx`
  - `apps/mission-control/src/pages/InboxPage.tsx`
  - `apps/mission-control/src/pages/InboxPage.test.tsx`
  - `apps/mission-control/src/pages/AgentDetailPage.tsx`
  - `apps/mission-control/src/pages/AgentDetailPage.test.tsx`
  - `apps/mission-control/src/pages/AgentsPage.tsx`
  - `apps/mission-control/src/pages/AgentsPage.test.tsx`
  - `apps/mission-control/src/pages/SettingsPage.tsx`
  - `apps/mission-control/src/pages/SettingsPage.test.tsx`
  - `apps/mission-control/src/components/AgentReleasePanel.tsx`
  - `apps/mission-control/src/components/HostAdapterBadge.tsx`
  - `apps/mission-control/src/components/SecretHealthPanel.tsx`
  - `apps/mission-control/src/components/SecretHealthPanel.test.tsx`
  - `apps/mission-control/src/components/AuditTimeline.tsx`
  - `apps/mission-control/src/components/AuditTimeline.test.tsx`
  - `apps/mission-control/src/components/UsagePanel.tsx`
  - `apps/mission-control/src/components/UsagePanel.test.tsx`
  - `apps/mission-control/src/pages/SecretsPage.tsx`
  - `apps/mission-control/src/pages/SecretsPage.test.tsx`
  - `apps/mission-control/src/pages/AuditPage.tsx`
  - `apps/mission-control/src/pages/AuditPage.test.tsx`
  - `apps/mission-control/src/pages/UsagePage.tsx`
  - `apps/mission-control/src/pages/UsagePage.test.tsx`
  - `apps/mission-control/src/lib/fixtures.ts`
  - `apps/mission-control/src/styles.css`

### Final verification evidence

Frontend:
- `npm --prefix apps/mission-control run test -- --run` → `19 files passed`, `52 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass

Backend targeted:
- `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest tests/api/test_mission_control.py tests/api/test_agents.py tests/api/test_release_management.py tests/api/test_organizations.py tests/services/test_mission_control_service.py -q` → `53 passed`

Backend full suite:
- `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest -q` → `458 passed, 5 warnings`

Known warnings:
- existing `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warnings in older tests

QC:
- fresh `gpt-5.4` XHIGH QC review approved the current `P6.5` diff with no remaining blocker-level findings

## Smallest safe next step for the next session

1. Keep Phase 6 closed.
2. Start any post-Phase-6 branch work only with a fresh bounded handoff from the master plan.

## Repo cleanup check already performed

- Searched for stray spec/plan files.
- No obviously foreign plan/spec files were found that clearly do not belong in this repo.
- No plan/spec files were deleted in this handoff prep because there was nothing high-confidence to remove without being reckless.
