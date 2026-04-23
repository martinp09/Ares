# Context

## Stable Facts
- Repo: `/Users/solomartin/Projects/Ares/.worktrees/fix-origin-main-supabase-persistence-wiring`
- Branch: `fix/origin-main-supabase-persistence-wiring`
- Base: `origin/main` at `a8e0145`
- Scope: finish the remaining Supabase persistence wiring on top of `origin/main`

## Current Scope
- Enterprise runtime collections now persist and hydrate in Supabase: organizations, memberships, catalog entries, agent installs, and release events.
- Ares scope snapshots now persist and hydrate in Supabase: plans, execution runs, and operator runs.
- Task persistence now matches the live Supabase contract, including scope keys and retry-dedupe semantics.
- Service seams now bind to the active backend at runtime and use rollback-safe shared-store transactions for install and release flows.
- Supabase flush restore now rolls back only rows touched by the failed request and avoids clobbering newer same-row commits.

## Current TODO
1. Review and merge `fix/origin-main-supabase-persistence-wiring` to `main`.
2. Keep follow-up scope narrow to post-merge Supabase regressions only.
3. Keep using `supabase start -x vector` on this machine until the Colima mount issue is fixed.

## Recent Change
- 2026-04-23: Completed the `origin/main` Supabase persistence wiring slice and closed the QC loop. Verification: `uv run pytest -q` -> `496 passed, 5 warnings`; targeted Supabase persistence pack -> `86 passed`; `npm --prefix apps/mission-control run test -- --run`, `typecheck`, and `build` all passed; `supabase db reset --local` passed after `supabase start -x vector`; `supabase stop` and `colima stop` were run afterward.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
