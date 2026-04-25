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
- Ares is not production-ready until hosted Ares runtime, Trigger.dev, Mission Control, provider webhooks, no-live smoke, live-recipient smoke, rollback, and production evidence are proven.
- No production migrations, production deploys, Trigger deploys, or live provider sends are allowed without the explicit gates.
- Mission Control must point at Ares runtime APIs; it must not call Supabase directly.

## Current TODO
1. Deploy Ares runtime preview after explicit approval to transmit required env secrets to Vercel project `production-readiness-afternoon`.
2. Run hosted `/health`, runtime auth rejection/acceptance, `/hermes/tools`, and `scripts/smoke_hermes_runtime_adapter.py`.
3. Deploy Trigger worker and Mission Control preview pointed at hosted Ares.
4. Configure provider webhooks and run no-live/provider-shape evidence; live sends require explicit operator-owned recipient flags.
5. Do not call Ares production-ready until production promotion evidence is complete.

## Recent Change
- 2026-04-25: Hardened preview evidence/production gates, moved `httpx` into runtime dependencies, added Vercel FastAPI entrypoint, linked Supabase preview project, applied five pending migrations, and verified full local backend/frontend/Trigger gates.
- 2026-04-24: Fixed the marketing lead confirmation-email path to use the same service-level Resend provider behavior as Mission Control's outbound email test; focused marketing/provider regressions pass locally, but a guarded live provider smoke still needs rerun evidence.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
