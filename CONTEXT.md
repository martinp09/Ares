# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Active worktree: `/Users/solomartin/Projects/Ares/.worktrees/production-readiness-afternoon`
- Branch: `codex/production-readiness-afternoon`
- Source branch: `origin/test/production-readiness-handoff`
- Production-readiness handoff: `docs/production-readiness-handoff.md`
- Production-readiness plan: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`
- Preview evidence: `docs/rollout-evidence/preview-2026-04-25.json`

## Current Scope
- This branch is a test/handoff branch for the remaining live-production wiring gates.
- Preview Supabase target `awmsrjeawcxndfnggoxw` is linked and migrations through `202604240001` are applied.
- Ares preview runtime is live at `https://production-readiness-afternoon-g1ul6k5zv.vercel.app`; Mission Control preview is live at `https://mission-control-k73vipe98-martins-projects-9600e79e.vercel.app`.
- Trigger project `proj_puouljyhwiraonjkpiki` deployed prod worker version `20260425.3`; preview branches/staging are unavailable in Trigger.
- Ares is not production-ready until provider webhooks, live-recipient smoke, rollback, and production evidence are proven.
- No live provider sends are allowed without explicit operator-owned recipient flags.
- Mission Control must point at Ares runtime APIs; it must not call Supabase directly.

## Current TODO
1. Configure provider webhooks to the Ares preview URLs in `docs/rollout-evidence/preview-2026-04-25.json`.
2. Run guarded live provider smoke only with explicit operator-owned phone/email values.
3. Run production promotion evidence after provider gates, rollback reference, exact commit match, and verified production Supabase target.
4. Do not call Ares production-ready until production promotion evidence is complete.

## Recent Change
- 2026-04-25: Hardened preview evidence/production gates, moved `httpx` into runtime dependencies, added Vercel FastAPI entrypoint, linked Supabase preview project, applied five pending migrations, and verified full local backend/frontend/Trigger gates.
- 2026-04-25: Deployed Ares preview, Mission Control preview, and Trigger prod worker; protected Vercel smoke passed for health/auth/tools/dashboard/run readback. Evidence is blocked only on provider webhook configuration and operator-owned live-recipient smoke.
- 2026-04-24: Fixed the marketing lead confirmation-email path to use the same service-level Resend provider behavior as Mission Control's outbound email test; focused marketing/provider regressions pass locally, but a guarded live provider smoke still needs rerun evidence.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
