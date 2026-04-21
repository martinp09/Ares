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

1. lock the product thesis: Ares is the runtime, not the main agent
2. treat source lanes, strategy lanes, and operational stages as separate first-class concepts
3. ship a combined probate outbound + lease-option inbound MVP tonight
4. preserve a thin contract-to-close skeleton so title, TC, and dispo fit later without a rewrite
5. keep Hermes/browser work outside Ares and keep Ares deterministic

## Current TODO

1. execute `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
2. use probate as the current outbound source lane and cold email as the current outbound method
3. harden lease-option inbound as a first-class MVP lane, not a sidecar
4. keep the two-lane MVP stable:
   - probate outbound via Instantly
   - lease-option inbound via marketing submit / booking / SMS
5. probate positive replies / interested events now create opportunities; expand only if later tasks require more stage wiring
6. lease-option booked contacts now create opportunities; operator-ready and broader stage wiring still remain
7. prioritize composite pain stacks such as `estate_of + tax_delinquent` when data is available
8. keep Supabase as the canonical backend for both live MVP lanes and keep the live smoke path passing
9. keep Mission Control additive:
   - `Lead Machine`
   - `Marketing`
   - `Pipeline`
10. finish the remaining shared control-plane Supabase lift in slices:
   - done: `commands`, `approvals`, `runs`, `events`, `artifacts`
   - done: managed-agent/session/turn/governance runtime tables now have a shared Supabase-backed transaction path
   - next: live remote smoke against the new shared control-plane migration and any follow-up schema cleanup it exposes

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
