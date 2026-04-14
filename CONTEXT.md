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
4. keep managed-agent primitives scaffolded in-memory until live Supabase wiring happens on Martin's MacBook
5. keep Mission Control read models and the native frontend shell scaffold-first until live backend/Supabase wiring is ready

## Current TODO

1. execute `docs/superpowers/plans/2026-04-13-mission-control-supabase-persistence-plan.md` on a separate persistence branch after the Mission Control contract branch is green
2. attach Trigger tasks to runtime run/artifact/event updates
3. finish operator/docs alignment across this repo and `Mailers AWF`
4. start the QC + devil's-advocate review loop once the remaining docs/schema commits are in
5. sync README, specs, wiki, CONTEXT, and memory to the shipped Mission Control read models and UI shell
6. treat `docs/superpowers/plans/2026-04-13-mission-control-finish-plan.md` as the contract-first release plan and the new persistence plan as the separate Supabase rollout track

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Current Runtime Surface`
2. `## Repo Conventions`
3. `## Environment Notes`
4. `## Open Work`
5. latest entry in `## Change Log`
