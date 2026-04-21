# Context
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
3. treat `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md` as the merged phased implementation source of truth
4. treat `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json` as the overnight loop handoff artifact
5. keep Phase 1 guardrails explicit and locked: counties are Harris, Tarrant, Montgomery, Dallas, Travis
6. keep Phase 1 lead rule explicit and locked: probate is primary and tax delinquency is an overlay
7. keep Phase 1 outreach rule explicit and locked: drafts require human approval before any send
8. keep the Phase 1 `/ares/run` runtime route wired in and stable for end-to-end API calls
9. keep the shared versioned Ares agent registry primitives in place (name/purpose/revisions/tool/risk/output-contract/active-revision)
10. keep the shared durable memory and deterministic tool-policy foundations in place for typed history, allowlisted tools, hard approvals, audit trails, and kill-switch control
11. keep the shared evaluation-loop foundations and Mission Control autonomy-visibility read model in place for lead/response/conversion quality plus false-positive/duplicate-work/operator-correction tracking
12. keep the Phase 2 planner and Phase 3 bounded execution stack wired: `/ares/plans` remains operator-review-first, `/ares/execution/run` launches bounded runs, and Mission Control autonomy visibility surfaces execution run state/results alongside planner review
13. keep Phase 4 execution + Mission Control workflow integration in place: execution runs invoke playbook/state/eval workflow logic, enforce high-risk approval policy checks, surface drift detection, and expose decision/failure explanations in autonomy visibility
14. keep Phase 5 guarded autonomous operator wiring in place: `/ares/operator/run` executes approved objectives inside policy gates, persists operator snapshots by scope, and surfaces operator decisions/exceptions in Mission Control autonomy visibility

## Current TODO

1. keep remote/live smoke checks passing for the Supabase-backed control plane
2. add broader stage wiring only where the business actually needs it next
3. model composite pain stacks such as `estate_of + tax_delinquent` more explicitly in scoring and Mission Control prioritization
4. keep browser acquisition and ambiguous research in Hermes or other drivers, not inside Ares
5. add durable Trigger jobs only where sync paths become operationally risky

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Runtime Architecture`
3. `## Current Runtime Surface`
4. `## Repo Conventions`
5. `## Environment Notes`
6. `## Open Work`
7. latest entry in `## Change Log`

## Read These Specs Next

1. `docs/superpowers/specs/2026-04-16-ares-real-estate-runtime-thesis-design.md`
2. `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
3. `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md`
4. `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json`
