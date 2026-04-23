---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-23T15:38:00Z"
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

### Phase 6 final closeout

- `P6.3` added release/host visibility to the Mission Control shell through the agents-first workflow.
- `P6.4` added read-only governance surfaces for secrets health, audit, usage, and settings.
- `P6.5` added org-aware navigation/filtering while keeping `business_id + environment` alive as secondary scope and preserving the non-Supabase path.
- Phase 6 remains closed unless a fresh blocker appears.

### Phase 7 current state

- `P7.1` backend/domain work is now implemented locally and verified.
- `P7.2` Mission Control catalog/install UI is now implemented locally and verified.
- `P7.3` marketplace-readiness metadata is now implemented locally and verified.
- The new Phase 7 branch state adds:
  - catalog entries that point at agent revisions
  - derived host/provider/skill/secret/release compatibility metadata
  - install lineage records that preserve source agent/revision context
  - `/catalog` and `/agent-installs` API surfaces
  - a bounded Mission Control catalog page + install wizard with pre-install compatibility visibility and install outcome messaging
  - explicit truth gates so fixture-backed catalog entries cannot be installed and non-internal org scope does not inherit internal fixture catalog entries
  - visibility metadata that supports `internal`, `private_catalog`, and `marketplace_candidate`, while `marketplace_published` stays fail-closed behind an explicit config gate
- Installs preserve runtime semantics by reusing the existing agent-creation contract rather than inventing a parallel execution path.

### Latest verification evidence

Phase 6 recorded branch evidence:
- `npm --prefix apps/mission-control run test -- --run` → `19 files passed`, `52 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass
- targeted backend gate on the branch closeout → `53 passed`
- backend full suite on the branch closeout → `458 passed, 5 warnings`
- fresh `gpt-5.4` XHIGH QC approved the Phase 6 closeout

P7.1 local backend evidence:
- `./.venv/bin/python -m pytest tests/db/test_catalog_repository.py tests/db/test_agent_install_repository.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` → `21 passed`
- `./.venv/bin/python -m pytest -q` → `465 passed, 5 warnings`

P7.2 local frontend evidence:
- `npm --prefix apps/mission-control run test -- --run src/App.test.tsx src/lib/api.test.ts src/pages/CatalogPage.test.tsx` → `31 passed`
- `npm --prefix apps/mission-control run test -- --run` → `20 files passed`, `58 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass

P7.3 local marketplace-readiness evidence:
- `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/api/test_agent_installs.py -q` → `6 passed`
- `./.venv/bin/python -m pytest tests/api/test_agents.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/db/test_catalog_repository.py -q` → `23 passed`
- `npm --prefix apps/mission-control run test -- --run` → `20 files passed`, `58 tests passed`
- `npm --prefix apps/mission-control run typecheck` → pass
- `npm --prefix apps/mission-control run build` → pass
- `./.venv/bin/python -m pytest -q` → `468 passed, 5 warnings`

Known warnings:
- existing `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warnings in older tests

## Recommended next slice

### Phase 7 merge pass

`P7.1`, `P7.2`, and `P7.3` are implemented, QC-reviewed, locally verified, and now include the post-review release-managed deactivation fix.

The Phase 7 merge blockers are closed:
- `marketplace_publication_enabled` is derived live instead of persisted as stale point-in-time truth
- catalog install UX now speaks in terms of selected target scope and explicitly reports when an install landed outside the current filtered view
- active-agent retirement now has a first-class release-management deactivation path, and the legacy `/agents/.../archive` active path delegates into it instead of regressing `origin/main`

Next up:
- merge the branch to `main` if the final review verdict is approved

## Repo cleanup check already performed

- Searched for stray spec/plan files.
- No obviously foreign plan/spec files were found that clearly do not belong in this repo.
- No plan/spec files were deleted in this handoff prep because there was nothing high-confidence to remove without being reckless.
