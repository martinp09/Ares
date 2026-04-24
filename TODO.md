---
title: "Ares Production Readiness TODO / Handoff"
status: active
updated_at: "2026-04-24T13:00:33Z"
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

Existing source plans remain background:

- `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`
- `docs/superpowers/plans/2026-04-24-ares-supabase-wiring-from-memory.md`
- `docs/production-promotion.md`
- `docs/preview-staging-rollout.md`
- `docs/hermes-ares-trigger-supabase-runbook.md`

## Current status

Ares is **code-wired** but **not yet live-production-wired**.

Completed in code:

- Supabase control-plane hydrate/persist adapter exists.
- Runtime API routes are mounted.
- Trigger runtime callbacks exist.
- Mission Control API routes and frontend API client exist.
- Lead-machine runtime routes exist.
- Provider adapters/readiness surfaces exist.
- Guarded preview and production readiness scripts exist.
- Python backend suite passed on latest main: `558 passed, 5 warnings`.

Not completed live:

- no verified hosted Supabase migration apply
- no deployed Ares runtime with all backends set to `supabase`
- no deployed Trigger workers calling hosted Ares
- no deployed Mission Control proven against hosted Ares API source
- no provider webhooks proven against hosted Ares
- no no-live hosted smoke evidence
- no guarded live provider smoke evidence
- no production rollback/backup evidence

## Production-readiness TODO

### 1. Preview/staging Supabase gate

- [ ] Link preview/staging Supabase project.
- [ ] Confirm `supabase/.temp/project-ref` equals the expected preview/staging ref.
- [ ] Run `scripts/preview_rollout_readiness.py --run-linked-dry-run`.
- [ ] Apply migrations with `supabase db push --linked` only after the dry-run passes.
- [ ] Record evidence in `docs/rollout-evidence/preview-YYYY-MM-DD.json`.

### 2. Preview/staging Ares runtime gate

- [ ] Deploy Ares from the same commit used for Supabase migration evidence.
- [ ] Set runtime backends to `supabase`:
  - `CONTROL_PLANE_BACKEND=supabase`
  - `MARKETING_BACKEND=supabase`
  - `LEAD_MACHINE_BACKEND=supabase`
  - `SITE_EVENTS_BACKEND=supabase`
- [ ] Verify `/health`.
- [ ] Verify protected routes reject unauthenticated calls.
- [ ] Verify protected routes accept `Authorization: Bearer <runtime-key>`.
- [ ] Prove Ares reads/writes Supabase-backed state.
- [ ] Append Ares runtime evidence to the preview evidence JSON.

### 3. Trigger.dev gate

- [ ] Configure Trigger with hosted Ares `RUNTIME_API_BASE_URL` and `RUNTIME_API_KEY`.
- [ ] Run `npm --prefix trigger run typecheck`.
- [ ] Deploy Trigger workers to preview/staging.
- [ ] Prove lifecycle callbacks update Ares runs/events/artifacts.
- [ ] Append Trigger evidence to the preview evidence JSON.

### 4. Mission Control gate

- [ ] Install frontend dependencies if missing.
- [ ] Run Mission Control typecheck/tests/build.
- [ ] Deploy Mission Control pointed at hosted Ares with `VITE_RUNTIME_API_BASE_URL`.
- [ ] Prove dashboard/inbox/runs/tasks load from Ares API source, not fixture fallback.
- [ ] Append Mission Control evidence to the preview evidence JSON.

### 5. Provider webhook / no-live smoke gate

- [ ] Configure TextGrid inbound/status webhook to hosted Ares.
- [ ] Configure Cal.com booking webhook to hosted Ares.
- [ ] Configure Instantly webhook to hosted Ares if cold outbound is in scope.
- [ ] Run `uv run python scripts/smoke_provider_readiness.py`.
- [ ] Run `uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends`.
- [ ] Prove Mission Control shows runs/leads/tasks/audit/usage/provider failures.
- [ ] Append no-live/provider evidence to preview evidence JSON.

### 6. Guarded live provider smoke gate

- [x] Run first local live provider smoke with AWF credentials and memory-backed Ares state.
- [x] Confirm TextGrid SMS can queue through marketing lead intake.
- [x] Confirm direct Mission Control Resend email test can queue.
- [ ] Fix marketing lead confirmation email side-effect path: local smoke showed `HTTP Error 403: Forbidden` there while `/mission-control/outbound/email/test` succeeded through the direct Resend provider service.
- [ ] Confirm operator-owned phone/email recipients for hosted smoke.
- [ ] Set explicit live smoke recipient flags for hosted smoke.
- [ ] Send exactly controlled hosted test SMS/email.
- [ ] Prove provider IDs/statuses/webhooks/receipts are captured.
- [ ] Append live provider smoke evidence to preview evidence JSON.

### 7. Production promotion gate

- [ ] Create production backup/rollback reference.
- [ ] Link production Supabase project.
- [ ] Run `scripts/production_promotion_readiness.py` with expected project ref, staged commit, staging evidence, backup reference, and `--acknowledge-production`.
- [ ] Apply production migrations only if the gate passes.
- [ ] Deploy production Ares from the exact staged commit.
- [ ] Deploy production Trigger workers from the exact staged commit.
- [ ] Deploy production Mission Control pointed at production Ares.
- [ ] Run production no-live smoke.
- [ ] Run optional guarded live provider smoke.
- [ ] Record production evidence in `docs/rollout-evidence/production-YYYY-MM-DD.json`.

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
