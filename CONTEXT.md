# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Active checkout: `/Users/solomartin/Projects/Ares`
- Branch: `main`
- Baseline before production patch: `902570240f777e9be0c16db59927042d16a48755`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Production wiring is live for runtime health/auth, Supabase-backed state, Trigger callbacks, Instantly reply webhooks, TextGrid SMS/status callbacks, Cal.com booking callbacks, and Resend email smoke.
- Dashboard utility polish is the next product slice; approved visual direction is `docs/design/ares-dashboard-theme-2026-04-25.md`.
- Production evidence: `docs/rollout-evidence/production-2026-04-25.json`
- Preview/current-main evidence: `docs/rollout-evidence/preview-2026-04-25.json`
- Finish-today plan: `docs/superpowers/plans/2026-04-25-ares-production-readiness-finish-today.md`

## Current TODO
1. Build the ARES themed dashboard UI from `docs/design/ares-dashboard-theme-2026-04-25.md`.
2. Optionally replace the REST rollback bundle with a native `pg_dump` once Supabase container DNS is fixed.
3. Preserve production evidence files as the handoff source of truth.

## Recent Change
- 2026-04-25: Production Ares deployed to public Vercel URL with provider-compatible callback auth/parsing.
- 2026-04-25: Instantly webhook `019dc29e-bd0f-7ceb-a8f6-1dd9af1a7645` configured to production Ares and provider test returned 200.
- 2026-04-25: TextGrid live SMS to `+13467725914` was received; signed form-encoded TextGrid callback returned 200.
- 2026-04-25: Cal.com webhook `3d941b34-6943-44ed-b9b0-8904ebab0978` is active and synthetic booking webhook returned 200.
- 2026-04-25: Resend live email smoke to `dejesusperales16@gmail.com` queued with provider id `4a9172b4-dd9d-403e-9b59-2cb2304cb7e1`.
- 2026-04-25: Supabase rollback bundle saved at `/Users/solomartin/Projects/Ares-backups/2026-04-25-awmsrjeawcxndfnggoxw`.
- 2026-04-25: Trigger prod env targets production Ares and worker version `20260425.6` is deployed; `run_4` callback smoke completed.
- 2026-04-25: Verification passed: backend pytest, Mission Control test/typecheck/build, Trigger typecheck, lock/diff checks, no-live full-stack smoke.
- 2026-04-25: Saved approved polished ARES dashboard theme mockup under `docs/design/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
