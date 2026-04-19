# Context

> Read this file first. Use it as the router only. Do not load all of `memory.md` by default.

## Stable Facts

- Repo: `/Users/solomartin/Projects/Ares`
- Purpose: reusable real-estate operating runtime that agent drivers can call into
- First operating driver: Hermes
- Source of truth:
  - `CONTEXT.md` = scope, TODOs, router
  - `memory.md` = master indexed memory

## Current Scope

1. keep the new repo, GitHub remote, Trigger.dev setup, and fresh Supabase baseline clean
2. keep the runtime/app split explicit: Hermes shell here, seller-ops legacy stays outside
3. implement the marketing control plane first
4. keep Mission Control portable: Trigger.dev backbone, Supabase state, platform-agnostic core, adapter-only integrations
5. keep Ares framed as the self-hosted operating system for distressed real-estate lead management

## Current TODO

1. replace the in-memory runtime store with Supabase-backed persistence
2. attach Trigger tasks to runtime run/artifact/event updates
3. propagate the Mission Control portability + Zo adapter stance across remaining operator/docs surfaces
4. start the QC + devil's-advocate review loop once the remaining docs/schema commits are in

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Runtime Architecture`
3. `## Current Runtime Surface`
4. `## Open Work`
5. latest entry in `## Change Log`

## Read These Specs Next

1. `docs/superpowers/specs/2026-04-16-ares-real-estate-runtime-thesis-design.md`
2. `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
3. `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
