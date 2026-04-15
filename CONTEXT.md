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
3. implement the lease-option marketing MVP first: lead capture, booking state, confirmations, non-booker sequence, and inbound SMS qualification
4. keep the current MVP path honest: provider wiring is live-ready and Supabase marketing persistence now has a verified smoke path
5. keep Mission Control read models and the native frontend shell aligned to live marketing operations, not just research scaffolds

## Current TODO

1. extend the verified Supabase smoke path from contacts/conversations to the rest of the marketing repos in live runtime execution
2. remove ambiguous phone-only inbound matching or add tenant-safe routing metadata to TextGrid webhooks
3. finish true sequence-state tracking in guards instead of inferring from booking status alone
4. sync README, specs, wiki, CONTEXT, and memory to the current lease-option MVP state

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Current Runtime Surface`
2. `## Repo Conventions`
3. `## Environment Notes`
4. `## Open Work`
5. latest entry in `## Change Log`
