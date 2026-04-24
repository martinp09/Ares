# Context

## Stable Facts
- Repo: `/Users/solomartin/Projects/Ares-full-stack-cohesion`
- Branch: `feature/ares-full-stack-cohesion-clean`
- Live plan: `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- Spec gate: `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md`

## Current Scope
- Execute the full-stack cohesion plan in gated slices.
- Phases 0/1, 2, 3, and 4 are complete and QC-approved in the clean worktree.
- No live Supabase migrations, provider sends, Trigger deploys, or production deploys have been run.
- The dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` remains preserved outside this clean worktree.

## Current TODO
1. Commit the Phase 4 Trigger runtime contract slice.
2. Start Phase 5 provider adapter cohesion next.
3. Keep `CONTROL_PLANE_BACKEND`, `MARKETING_BACKEND`, `LEAD_MACHINE_BACKEND`, and `SITE_EVENTS_BACKEND` memory-backed for local smoke unless a Supabase slice explicitly starts.

## Recent Change
- 2026-04-24: Phase 4 tightened Trigger job IDs, lifecycle callbacks, queue keys, and callback persistence. Full backend/frontend/Trigger gates are green.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
