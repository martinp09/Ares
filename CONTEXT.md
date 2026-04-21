# Context
## Stable Facts

- Repo: `/Users/solomartin/Projects/Ares`
- Purpose: reusable operating runtime and control plane that agent drivers call into
- Source of truth:
  - `CONTEXT.md` = branch router / current scope
  - `memory.md` = indexed master memory

## Current Scope

1. branch: `feature/mission-control-enterprise-backlog`
2. treat `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md` as the canonical execution plan for this branch
3. treat these as live source inputs:
   - `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
   - `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
4. build on current `main`; do not re-do already landed Ares CRM / lead-machine phases
5. preserve existing Supabase wiring and extend it additively
6. keep the product model explicit:
   - agents are the product unit
   - Mission Control is the operator cockpit
   - skills are reusable procedures
   - host runtimes are adapters
7. current backlog focus after the merged baseline:
   - org tenancy + actor context
   - agent deployment / host adapters
   - enterprise controls
   - release lifecycle
   - Mission Control productization
   - internal catalog later

## Current TODO

1. execute Phase 0 and Phase 1 of the 2026-04-21 master plan
2. re-activate the enterprise platform plan as a live source plan
3. keep Mission Control and enterprise backlog scope merged in this branch only
4. do not disturb the separate Supabase persistence branch unless a later phase explicitly requires it

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Runtime Architecture`
3. `## Current Runtime Surface`
4. `## Open Work`
5. latest entry in `## Change Log`
