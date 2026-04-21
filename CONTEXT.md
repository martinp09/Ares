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

1. keep the runtime/app split explicit: Hermes shell here, seller-ops legacy stays outside
2. keep Ares framed as the self-hosted operating system for distressed real-estate lead management
3. keep the two live lanes stable on Supabase:
   - probate outbound via Instantly
   - lease-option inbound via marketing submit / booking / SMS
4. keep Mission Control additive and portable:
   - `Lead Machine`
   - `Marketing`
   - `Pipeline`
5. keep the shared control-plane Supabase lift complete and smokeable across commands, approvals, runs, events, artifacts, sessions, turns, RBAC, audit, and runtime projections

## Current TODO

1. keep remote/live smoke checks passing for the Supabase-backed control plane
2. add broader stage wiring only where the business actually needs it next
3. model composite pain stacks such as `estate_of + tax_delinquent` more explicitly in scoring and Mission Control prioritization
4. keep browser acquisition and ambiguous research in Hermes or other drivers, not inside Ares
5. add durable Trigger jobs only where sync paths become operationally risky

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Current Runtime Surface`
3. `## Repo Conventions`
4. `## Environment Notes`
5. `## Open Work`
6. latest entry in `## Change Log`
