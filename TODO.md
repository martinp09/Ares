---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-25T04:10:00Z"
repo: "martinp09/Ares"
local_checkout: "/Users/solomartin/Projects/Ares"
current_branch: "main"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

Ares is production-ready for a controlled live operator rollout.

Live production evidence:

- Runtime: `https://production-readiness-afternoon.vercel.app`
- Supabase project: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`
- Trigger worker: `20260425.6`
- Production evidence: `docs/rollout-evidence/production-2026-04-25.json`
- Preview/current-main evidence: `docs/rollout-evidence/preview-2026-04-25.json`

Proven live wiring:

- Runtime health/auth on production Vercel.
- Supabase-backed runtime state.
- Trigger lifecycle callbacks.
- Instantly reply webhook.
- TextGrid SMS send and signed form-encoded status callback.
- Cal.com booking webhook.
- Resend live email smoke.
- Rollback bundle at `/Users/solomartin/Projects/Ares-backups/2026-04-25-awmsrjeawcxndfnggoxw`.

Known caveat:

- Native `pg_dump` backup is not captured because the Supabase CLI container could not resolve the Supabase DB host from Colima. A REST table-export rollback bundle exists instead.

## Next product slice

### 1. Dashboard UI polish

- [ ] Build the approved ARES dashboard theme direction.
- [ ] Use `docs/design/ares-dashboard-theme-2026-04-25.md` as the design source.
- [ ] Keep it a real dense Mission Control dashboard, not a game menu.
- [ ] Keep gothic/flame treatment concentrated around the `ARES` title and subtle dashboard accents.
- [ ] Preserve readability, operator density, and existing Mission Control workflows.

### 2. Production hardening follow-up

- [ ] Replace the REST rollback bundle with native `pg_dump` once Colima/Supabase DB DNS is fixed, if strict database restore fidelity is required.
- [ ] Add production monitoring/alerts for provider callback failures.
- [ ] Keep production evidence files updated after any provider or deployment changes.

## Hard rules

- Do not make Mission Control frontend call Supabase directly.
- Do not run live SMS/email without explicit approved recipients.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the evidenced commit.
- Do not rewrite already-applied baseline migrations in place.

## Minimum verification before merge/push

```bash
git diff --check
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
```
