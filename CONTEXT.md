# Context

## Stable Facts
- Repo: `/Users/solomartin/Projects/Ares-full-stack-cohesion`
- Branch: `feature/ares-full-stack-cohesion-clean`
- Live plan: `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- Spec gate: `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md`

## Current Scope
- Execute the full-stack cohesion plan in gated slices.
- Phases 0/1 through 9 are complete and QC-approved in the clean worktree.
- No live Supabase migrations, provider sends, Trigger deploys, or production deploys have been run.
- The dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` remains preserved outside this clean worktree.

## Current TODO
1. Commit Phase 9 end-to-end local smoke.
2. Start Phase 10 preview/staging rollout readiness next.
3. Do not run live Supabase migrations, provider sends, Trigger deploys, or production deploys unless the target is explicitly verified safe.

## Recent Change
- 2026-04-24: Phase 9 added deterministic in-process full-stack smoke coverage for Hermes, Ares, Trigger callbacks, marketing provider webhooks, Mission Control, audit, usage, tasks, messages, and bookings. Full gates and fresh QC are green.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
