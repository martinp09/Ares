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
- Continue Phase 6 bounded Mission Control productization on the active non-Supabase path.
- Keep Mission Control as the operator cockpit and agents as the product unit.
- Do not touch Supabase, migrations, or persistence rewiring in this environment.
- Keep all changes additive and preserve existing non-Supabase seams.

## Current TODO
1. Finish `P6.2` QC blockers in the read-only agent-detail slice.
2. Re-run frontend + backend verification.
3. Get XHIGH QC approval before moving to the next Phase 6 slice.

## Recent Change
- 2026-04-23: P6.2 now has a real read-only agent-detail workflow in Mission Control with bounded lifecycle/revisions/release/secrets/audit/usage/turns surfaces, degraded-section handling, latest-release ordering fixes, search/selection safety, and an agents-surface retry path; the slice is still open because QC found remaining truthfulness blockers around stale context-panel state, degraded summary identity fallback, and shell/source-label reconciliation after agent recovery.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
