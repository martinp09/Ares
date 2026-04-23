# Context

## Stable Facts
- Repo: `/root/.config/superpowers/worktrees/Hermes-Central-Command/mission-control-enterprise-backlog`
- Branch: `feature/mission-control-enterprise-backlog`
- Canonical scope doc: `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md`
- Canonical slice order: `docs/superpowers/plans/2026-04-22-mission-control-enterprise-backlog-sliced-execution-plan.md`
- Live source inputs:
  - `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
  - `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`

## Current Scope
- Phase 6 Mission Control productization is complete through `P6.5` on the active non-Supabase path.
- Phase 7 is now implemented locally through `P7.3` on top of that Phase 6 state.
- Keep Mission Control as the operator cockpit and agents as the product unit.
- Do not touch Supabase, migrations, or persistence rewiring in this environment.
- Keep all changes additive and preserve existing non-Supabase seams.

## Current TODO
1. Keep Phase 6 closed unless a fresh blocker appears.
2. Treat Phase 7 (`P7.1` + `P7.2` + `P7.3`) as implemented, QC-fixed, and green locally on the active branch.
3. Next move is commit/push for the combined Phase 7 diff.

## Recent Change
- 2026-04-23: `P7.3` is now implemented locally on top of the already-landed `P7.1`/`P7.2` work. Agent/catalog visibility now carries marketplace-readiness metadata through the backend and Mission Control UI, `marketplace_published` is blocked by default behind `marketplace_publish_enabled`, catalog entries expose visibility + publication-enabled state, and installs preserve the source visibility without implying public launch. The QC follow-up fixes are now in too: `marketplace_publication_enabled` is derived live instead of stored as stale truth, and catalog install messaging now explicitly distinguishes selected target scope from the current filtered view. Fresh verification shows `npm --prefix apps/mission-control run test -- --run` = `20 files passed`, `59 tests passed`, `npm --prefix apps/mission-control run typecheck` = pass, `npm --prefix apps/mission-control run build` = pass, and `./.venv/bin/python -m pytest -q` = `469 passed, 5 warnings`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
