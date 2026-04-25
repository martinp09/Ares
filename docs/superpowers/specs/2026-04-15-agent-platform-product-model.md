# Agent Platform Product Model

> Phase 0 product-language lock for Ares.
> Historical scope: documentation only for the April 15 dogfood slice.
> Superseded on 2026-04-25 by production Supabase/provider wiring evidence in `docs/rollout-evidence/production-2026-04-25.json`.

## Goal

State the product model clearly before more runtime, UI, or persistence work lands.

## Product Model

Ares is the agent platform.
Mission Control is the native operator cockpit inside that platform.

The core units are:

- Agent = the product unit
- Agent revision = the deployable release artifact
- Skill = a reusable procedure an agent can bind to
- Session = an execution thread pinned to one agent revision
- Host runtime = an adapter that executes the revision
- App = an operator surface, not the product unit

## Host-Adapter Rule

Host runtimes are adapters, not the platform identity.

For this slice:
- Trigger.dev is the current enabled execution infrastructure
- Trigger.dev callback fields stay infrastructure details, not generic agent identity
- future Codex or Anthropic runtimes must fit the same adapter seam
- runtime-specific config belongs inside an adapter-specific envelope, not in the base agent identity

## Operator Model

Mission Control is the operator cockpit.
It exists to:
- launch and supervise agents
- inspect runs, approvals, sessions, and artifacts
- show operational state without becoming a separate product model

`apps/mission-control/` is therefore a platform surface, not the packaging unit for deployment.

## Historical Phase-0 Boundary

This branch originally stayed aligned to the April 15 dogfood slice:
- keep the in-memory agent, session, permission, outcome, asset, and Mission Control scaffolds
- keep current `business_id` and `environment` runtime contracts intact
- keep the Mission Control happy path fixture-backed where the branch already does so
- defer production Supabase wiring and org/auth expansion until later phases

## Non-Goals In This Phase

- no runtime wiring changes
- no backend contract changes
- no persistence cutover
- no attempt to make Trigger.dev the permanent platform abstraction

## Repo Mapping

- `app/` = deterministic platform runtime and typed APIs
- `apps/mission-control/` = operator cockpit
- `trigger/` = current host infrastructure adapter path
- `supabase/` = system-of-record schema and production persistence target

## Phase-0 Decision

When Ares is described in docs, code comments, or UI copy:
- say agent platform, not app platform
- say agents are the product unit
- say skills are reusable procedures
- say host runtimes are adapters
- say Mission Control is the operator cockpit
- say Trigger.dev is current infrastructure, not the platform identity
- say Supabase-backed production wiring is live for the runtime/provider lanes proven in production evidence, while local development can still use memory-backed stores
