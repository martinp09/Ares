# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Local test checkout: `/tmp/ares-production-readiness`
- Branch: `test/production-readiness-handoff`
- Base commit: `0c14769` (`origin/main`)
- Production-readiness handoff: `docs/production-readiness-handoff.md`
- Production-readiness plan: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`

## Current Scope
- This branch is a test/handoff branch for the remaining live-production wiring gates.
- Ares is code-wired, but not production-ready until live Supabase, Ares runtime, Trigger.dev, Mission Control, providers, smoke evidence, and rollback evidence are proven.
- No production migrations, production deploys, Trigger deploys, or live provider sends are performed by this branch.
- Mission Control must point at Ares runtime APIs; it must not call Supabase directly.

## Current TODO
1. Use `docs/production-readiness-handoff.md` as the operator checklist.
2. Execute the plan phases in `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`.
3. Create rollout evidence files under `docs/rollout-evidence/` as each hosted gate is proven.
4. Do not call Ares fully production-ready until the final acceptance gate and production evidence are complete.

## Recent Change
- 2026-04-24: Added Harris probate rollout evidence: 202 last-week rows, 113 keep-now rows, 12 priority heirship/title-friction case-detail enrichments, and an Ares memory-backed intake simulation that bridged all 12 priority cases into canonical leads while leaving HCAD/tax overlay as the next backend gap.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
