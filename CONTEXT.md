# Context

> Read this file first. Use it as the router only. Do not load all of `memory.md` by default.

## Stable Facts

- Repo: `/home/workspace/Hermes-Central-Command`
- Purpose: reusable Hermes-controlled business runtime
- Operating model: generalist core first, industry packs second
- First optimization target: real estate
- Source of truth:
  - `CONTEXT.md` = scope, TODOs, router
  - `memory.md` = master indexed memory

## Current Scope

1. keep the new repo, GitHub remote, Trigger.dev setup, and fresh Supabase baseline clean
2. keep the runtime/app split explicit: Hermes shell here, seller-ops legacy stays outside
3. implement the marketing control plane first
4. keep managed-agent persistence on the additive Supabase rollout track without making Mission Control durable truth
5. keep Mission Control read models and the native frontend shell scaffold-first until live backend/Supabase wiring is ready

## Current TODO

1. execute `docs/superpowers/plans/2026-04-13-mission-control-supabase-persistence-plan.md` on a separate persistence branch after the Mission Control contract branch is green
   - progress: runtime contract freeze slice 1 landed on `feature/mission-control-supabase-persistence` (`business_id` int for commands/approvals/runs + `replay_source_run_id` in run contract)
   - progress: persistence compatibility slice landed with additive migration `202604130002_mission_control_runtime_persistence.sql`, repo-only SQL/runtime mapping seams, and green Python test suite (`70 passed`)
   - progress: local Colima mount-socket failure reproduced and scoped workaround validated (`supabase start --exclude vector --exclude logflare`, `supabase db reset --local`, `supabase stop`)
   - progress: runtime-core Supabase adapter slice landed in `app/db` for commands/approvals/runs/events/artifacts, plus explicit repository persistence hooks in runtime-core services (`uv run pytest -q` now `74 passed`)
   - progress: managed-agent Supabase adapter slice landed in `app/db` for agents/revisions/sessions/session events plus permissions/outcomes/assets migrations/tests (`uv run pytest -q` now `89 passed`)
   - progress: local Supabase reset verified through additive migrations `202604130001` to `202604130005`, then fully shut down (`supabase stop`, `colima stop`)
2. attach Trigger tasks to runtime run/artifact/event updates
3. derive Mission Control projections from canonical persisted runtime/conversation data instead of in-memory thread state
4. finish operator/docs alignment across this repo and `Mailers AWF`
5. start the QC + devil's-advocate review loop once the remaining docs/schema commits are in
6. sync README, specs, wiki, CONTEXT, and memory to the shipped Mission Control read models and Supabase rollout status

## Handoff Next Steps

1. replace the in-memory `mission_control_threads` write path with a rebuildable projection derived from canonical runtime/conversation data
2. keep Mission Control read-side only; do not introduce durable operator-thread truth
3. decide whether the projection needs additive conversation/read-state tables or can be built from existing canonical records plus derived state
4. attach Trigger task updates to canonical run/event/artifact persistence after the Mission Control projection boundary is settled
5. run QC on the Mission Control projection plan before adding new migrations

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Current Runtime Surface`
3. `## Environment Notes`
4. `## Open Work`
5. `## Handoff Notes`
6. latest entry in `## Change Log`
