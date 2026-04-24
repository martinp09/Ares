# Context

## Stable Facts
- Repo: `/Users/solomartin/Projects/Ares-full-stack-cohesion`
- Branch: `feature/ares-full-stack-cohesion-clean`
- Live plan: `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- Spec gate: `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md`

## Current Scope
- Execute the full-stack cohesion plan in gated slices.
- Phases 0/1 through 8 are complete and QC-approved in the clean worktree.
- No live Supabase migrations, provider sends, Trigger deploys, or production deploys have been run.
- The dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` remains preserved outside this clean worktree.

## Current TODO
1. Commit Phase 8 runtime observability.
2. Start Phase 9 end-to-end local smoke next.
3. Keep `CONTROL_PLANE_BACKEND`, `MARKETING_BACKEND`, `LEAD_MACHINE_BACKEND`, and `SITE_EVENTS_BACKEND` memory-backed for local smoke unless a Supabase slice explicitly starts.

## Recent Change
- 2026-04-24: Phase 8 added nonfatal runtime audit/usage emission with agent-scoped command, approval, run, Trigger lifecycle, replay, and Supabase command persistence coverage. Full gates and fresh QC are green.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
