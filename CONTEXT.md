# Context

## Stable Facts
- Repo: `/Users/solomartin/Projects/Ares-full-stack-cohesion`
- Branch: `feature/ares-full-stack-cohesion-clean`
- Live plan: `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- Spec gate: `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md`

## Current Scope
- Execute the full-stack cohesion plan in gated slices.
- Phase 0/1 is the active clean slice: spec, env contract, runbook, config tests, Trigger contract tests.
- No live Supabase migrations, provider sends, or production deploys in this slice.
- The dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` remains preserved outside this clean worktree.

## Current TODO
1. Finish Phase 0/1 QC gate.
2. Keep `CONTROL_PLANE_BACKEND`, `MARKETING_BACKEND`, `LEAD_MACHINE_BACKEND`, and `SITE_EVENTS_BACKEND` memory-backed for local smoke unless a Supabase slice explicitly starts.
3. Start Phase 2 only after Phase 0/1 is green and the dirty persistence slice is intentionally reconciled.

## Recent Change
- 2026-04-24: Created clean worktree `feature/ares-full-stack-cohesion-clean`; restored the remote mega-plan docs; added the full-stack cohesion spec gate, local env/runbook contract, Vite proxy auth, and Phase 1 config/Trigger contract tests.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
