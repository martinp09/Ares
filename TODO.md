---
title: "Ares Production Readiness TODO / Handoff"
status: active
updated_at: "2026-04-25T01:55:00Z"
repo: "martinp09/Ares"
local_checkout: "/tmp/ares-production-readiness"
current_branch: "test/production-readiness-handoff"
base_commit: "0c14769"
---

# Ares Production Readiness TODO / Handoff

## Live pointer

This branch exists to answer one question cleanly:

> What exactly remains before Ares can honestly be called fully wired and production ready?

Primary handoff:

- `docs/production-readiness-handoff.md`

Execution plan:

- `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md`

Curative-title workflow hub:

- `docs/curative-title-wiki/index.md`

Latest curative-title packet test:

- `docs/rollout-evidence/contact-candidate-packets-2026-04-24/REPORT.md`

Latest HCAD/property match test:

- `docs/rollout-evidence/hcad-match-test-2026-04-24/REPORT.md`

Latest tax overlay discovery:

- `docs/rollout-evidence/tax-overlay-discovery-2026-04-24/REPORT.md`

Latest tax overlay adapter smoke:

- `docs/rollout-evidence/tax-overlay-adapters-2026-04-24/REPORT.md`

Existing source plans remain background:

- `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- `docs/superpowers/plans/2026-04-24-ares-supabase-wiring-from-memory.md`
- `docs/production-promotion.md`
- `docs/preview-staging-rollout.md`
- `docs/hermes-ares-trigger-supabase-runbook.md`

## Current status

Ares production runtime is live at `https://production-readiness-afternoon.vercel.app` and is wired to Supabase-backed runtime state, Trigger callbacks, Instantly reply webhooks, and TextGrid SMS/status callbacks.

Completed current-main production wiring:

- Runtime production health returns 200; protected routes reject missing auth and accept runtime auth.
- Supabase project `awmsrjeawcxndfnggoxw` is linked and migrated; `limitless/prod` tenant exists.
- Trigger project `proj_puouljyhwiraonjkpiki` prod env points at production Ares; worker version `20260425.6` deployed.
- Instantly webhook `019dc29e-bd0f-7ceb-a8f6-1dd9af1a7645` targets production Ares and provider-side test returned 200.
- TextGrid live SMS to operator phone `+13467725914` was received; signed form-encoded status callback returned 200.
- Evidence files validate as ready:
  - `docs/rollout-evidence/preview-2026-04-25.json`
  - `docs/rollout-evidence/production-2026-04-25.json`
- Verification passed: backend pytest, Mission Control tests/typecheck/build, Trigger typecheck, lock/diff checks, no-live full-stack smoke.

Remaining caveats:

- Native `pg_dump` backup is not captured because the Supabase CLI container could not resolve the Supabase DB host from Colima; a REST table-export rollback bundle exists instead.
- Dashboard utility polish is still intentionally deferred.

## Production-readiness TODO

### 1. Commit and push current production fixes

- [ ] Review current diff on `main`.
- [ ] Commit provider-compatible webhook/runtime auth fixes and evidence docs.
- [ ] Push to `origin/main` or open PR, depending on branch policy.

### 2. Provider completion evidence

- [x] Register Cal.com booking webhook to production Ares.
- [x] Send a booked test event with `lead_id` metadata.
- [x] Run exactly one controlled hosted Resend smoke to operator email.
- [x] Record provider IDs/status evidence in `docs/rollout-evidence/production-2026-04-25.json`.

### 3. Promotion discipline hardening

- [x] Capture rollback bundle for `awmsrjeawcxndfnggoxw` under `/Users/solomartin/Projects/Ares-backups/2026-04-25-awmsrjeawcxndfnggoxw`.
- [ ] Optionally replace REST export bundle with native `pg_dump` once Colima/Supabase DB DNS is fixed.
- [ ] Keep `docs/rollout-evidence/production-2026-04-25.json` updated with any new evidence.

## Hard rules

- Do not install Ares into Hermes.
- Do not make Hermes, Trigger.dev, providers, or Mission Control the source of truth.
- Do not let Mission Control frontend call Supabase directly.
- Do not rewrite already-applied baseline migrations in place.
- Do not run live SMS/email without explicit approved recipient flags.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the staged/evidenced commit.
- Do not run production migrations unless the linked Supabase project ref is verified.

## Minimum local verification before merging this handoff branch

```bash
git diff --check
uv run pytest -q
```

Optional once Node dependencies exist:

```bash
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
```

## Definition of production ready

Ares is production-ready only when:

- [ ] hosted Supabase persistence is applied and verified
- [ ] hosted Ares runtime is writing Supabase-backed state
- [ ] Trigger.dev workers call hosted Ares and report lifecycle back
- [ ] Mission Control uses hosted Ares API data, not fixtures
- [ ] provider webhooks round-trip into Ares
- [ ] no-live smoke passes in hosted environment
- [ ] guarded live provider smoke passes with approved recipients
- [ ] production evidence JSON exists
- [ ] rollback/backup reference exists
