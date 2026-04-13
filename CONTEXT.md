# Context

> Read this file first. Use it as the router only. Do not load all of `memory.md` by default.

## Stable Facts

- Repo: `/Users/solomartin/Projects/Hermes Central Command`
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

1. replace the in-memory runtime store with Supabase-backed persistence
2. attach Trigger tasks to runtime run/artifact/event updates
3. finish operator/docs alignment across this repo and `Mailers AWF`
4. start the QC + devil's-advocate review loop once the remaining docs/schema commits are in
5. wire the Mission Control frontend shell to native backend read-model routes when phase-6 backend work lands

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Current Runtime Surface`
2. `## Repo Conventions`
3. `## Environment Notes`
4. `## Open Work`
5. latest entry in `## Change Log`
