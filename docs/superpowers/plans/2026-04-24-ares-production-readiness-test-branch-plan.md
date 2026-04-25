# Ares Production Readiness Test Branch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ares from code-wired into fully live-wired and production-ready by proving Supabase, Ares runtime, Trigger.dev, Mission Control, and provider loops in hosted environments.

**Architecture:** Hermes remains the operator shell. Ares remains the deterministic runtime/API/state layer. Supabase is canonical persistence, Trigger.dev is async schedule/retry infrastructure, providers own external delivery, and Mission Control only talks to Ares runtime APIs.

**Tech Stack:** FastAPI, Supabase/PostgREST, Trigger.dev, React/Vite Mission Control, TextGrid, Resend/email, Cal.com, Instantly, Python pytest smoke/readiness scripts.

---

## Current branch purpose

This is a **test/handoff branch**, not a production deployment branch.

Branch: `test/production-readiness-handoff`  
Base commit: `0c14769` (`origin/main`)  
Primary handoff doc: `docs/production-readiness-handoff.md`

## Files in this handoff branch

- Modify: `CONTEXT.md` — route future sessions toward the production-readiness gate.
- Modify: `TODO.md` — replace vague next gate with concrete remaining production-readiness TODOs.
- Modify: `README.md` — add visible production-readiness pointer.
- Modify: `memory.md` — record the branch purpose and current production-readiness status.
- Create: `docs/production-readiness-handoff.md` — layman + technical checklist for fully wired production readiness.
- Create: `docs/superpowers/plans/2026-04-24-ares-production-readiness-test-branch-plan.md` — this implementation plan.

---

## Phase 0: Baseline already satisfied on this branch

- [x] Created clean branch from latest `origin/main`.
- [x] Confirmed latest backend code includes Supabase control-plane hydration/persistence rather than the older `NotImplementedError` stub.
- [x] Confirmed Python backend suite passes on latest main: `558 passed, 5 warnings`.
- [x] Confirmed Node/Mission Control verification requires installing dependencies in the worktree before typecheck/build/test can run.

---

## Phase 1: Preview/staging environment wiring

### Task 1: Verify the target Supabase project before touching migrations

**Files:**
- Read: `supabase/config.toml`
- Read: `supabase/.temp/project-ref` after linking
- Use: `scripts/preview_rollout_readiness.py`
- Use: `scripts/rollout_evidence.py`
- Evidence: `docs/rollout-evidence/preview-YYYY-MM-DD.json`

- [ ] **Step 1: Create the non-secret preview evidence skeleton**

```bash
uv run python scripts/rollout_evidence.py init \
  docs/rollout-evidence/preview-YYYY-MM-DD.json \
  --environment preview \
  --commit "$(git rev-parse HEAD)"
```

Expected: JSON file exists with explicit `TODO` statuses and no secret values.

- [ ] **Step 2: Link the preview/staging Supabase project**

```bash
supabase link --project-ref <preview-project-ref>
```

Expected: `supabase/.temp/project-ref` contains `<preview-project-ref>`.

- [ ] **Step 3: Run the guarded preview dry-run**

```bash
uv run python scripts/preview_rollout_readiness.py \
  --expected-project-ref <preview-project-ref> \
  --run-linked-dry-run
```

Expected: readiness output reports the linked ref matches and the dry-run passed.

- [ ] **Step 4: Stop if the project ref mismatches**

If the project ref is not exactly `<preview-project-ref>`, stop. Do not run `supabase db push`.

- [ ] **Step 5: Apply preview/staging migrations**

```bash
supabase db push --linked
supabase migration list --linked
```

Expected: migration chain includes the Ares runtime migrations, including core control-plane, lead-machine, managed-agent, and command agent revision scope migrations.

- [ ] **Step 6: Fill preview evidence JSON**

Patch `docs/rollout-evidence/preview-YYYY-MM-DD.json`:

```json
{
  "commit": "<git-sha>",
  "environment": "preview",
  "supabase_project_ref": "<preview-project-ref>",
  "migration_dry_run": "passed",
  "migration_apply": "passed",
  "notes": ["Preview Supabase migrations applied from verified project ref."]
}
```

- [ ] **Step 7: Validate preview evidence still names the remaining TODOs**

```bash
uv run python scripts/rollout_evidence.py validate docs/rollout-evidence/preview-YYYY-MM-DD.json
```

Expected: `blocked` until later gates replace every `TODO`; `todo_fields` is the remaining operator checklist.

- [ ] **Step 8: Commit preview evidence without secrets**

```bash
git add docs/rollout-evidence/preview-YYYY-MM-DD.json
git commit -m "docs: record preview supabase rollout evidence"
```

---

### Task 2: Deploy Ares preview/staging runtime with Supabase-backed state

**Files:**
- Read: `.env.example`
- Read: `docs/hermes-ares-trigger-supabase-runbook.md`
- Use: hosting provider env settings
- Evidence: `docs/rollout-evidence/preview-YYYY-MM-DD.json`

- [ ] **Step 1: Configure runtime env**

Set these in the preview/staging runtime host:

```bash
RUNTIME_API_KEY=<strong-runtime-key>
CONTROL_PLANE_BACKEND=supabase
MARKETING_BACKEND=supabase
LEAD_MACHINE_BACKEND=supabase
SITE_EVENTS_BACKEND=supabase
SUPABASE_URL=<preview-supabase-url>
SUPABASE_SERVICE_ROLE_KEY=<preview-service-role-key>
TRIGGER_SECRET_KEY=<preview-trigger-secret>
TEXTGRID_STATUS_CALLBACK_URL=https://<preview-ares>/marketing/webhooks/textgrid
```

- [ ] **Step 2: Deploy Ares runtime**

Deploy the same commit recorded in preview evidence.

- [ ] **Step 3: Verify health**

```bash
curl -fsS https://<preview-ares>/health
```

Expected:

```json
{"status":"ok"}
```

- [ ] **Step 4: Verify protected route rejects unauthenticated requests**

```bash
curl -i https://<preview-ares>/hermes/tools
```

Expected: HTTP `401` or `403`.

- [ ] **Step 5: Verify protected route accepts runtime key**

```bash
curl -fsS \
  -H "Authorization: Bearer <runtime-key>" \
  https://<preview-ares>/hermes/tools
```

Expected: JSON includes `tools`.

- [ ] **Step 6: Update evidence JSON**

Patch `docs/rollout-evidence/preview-YYYY-MM-DD.json` to include:

```json
{
  "ares_runtime_url": "https://<preview-ares>",
  "runtime_health": "passed",
  "runtime_auth": "passed"
}
```

- [ ] **Step 7: Commit runtime evidence**

```bash
git add docs/rollout-evidence/preview-YYYY-MM-DD.json
git commit -m "docs: record preview ares runtime evidence"
```

---

## Phase 2: Trigger.dev runtime wiring

### Task 3: Deploy Trigger workers against preview/staging Ares

**Files:**
- Read: `trigger/src/lead-machine/runtime.ts`
- Read: `trigger/src/runtime/reportRunLifecycle.ts`
- Use: Trigger.dev project env settings
- Evidence: `docs/rollout-evidence/preview-YYYY-MM-DD.json`

- [ ] **Step 1: Configure Trigger env**

```bash
RUNTIME_API_BASE_URL=https://<preview-ares>
RUNTIME_API_KEY=<runtime-key>
TRIGGER_SECRET_KEY=<preview-trigger-secret>
```

- [ ] **Step 2: Typecheck Trigger package**

```bash
npm --prefix trigger run typecheck
```

Expected: exits 0.

- [ ] **Step 3: Deploy Trigger workers**

Use the repo’s Trigger deploy command for the configured project/environment.

- [ ] **Step 4: Run a lifecycle callback smoke through Ares**

Create a command/run through Ares and verify Trigger callbacks can update it:

```bash
curl -fsS \
  -H "Authorization: Bearer <runtime-key>" \
  -H "Content-Type: application/json" \
  -X POST https://<preview-ares>/hermes/tools/run_market_research/invoke \
  -d '{"business_id":"limitless","environment":"preview","idempotency_key":"preview-trigger-smoke-001","payload":{"topic":"preview trigger smoke"}}'
```

Then call started/completed callback for the returned `run_id`:

```bash
curl -fsS \
  -H "Authorization: Bearer <runtime-key>" \
  -H "Content-Type: application/json" \
  -X POST https://<preview-ares>/trigger/callbacks/runs/<run_id>/started \
  -d '{"trigger_run_id":"preview-trigger-smoke"}'

curl -fsS \
  -H "Authorization: Bearer <runtime-key>" \
  -H "Content-Type: application/json" \
  -X POST https://<preview-ares>/trigger/callbacks/runs/<run_id>/completed \
  -d '{"trigger_run_id":"preview-trigger-smoke"}'
```

Expected: run status and audit/usage data are visible through Ares endpoints and persisted in Supabase-backed state.

- [ ] **Step 5: Update evidence JSON**

Add:

```json
{
  "trigger_project_ref": "<trigger-ref>",
  "trigger_runtime_callbacks": "passed"
}
```

- [ ] **Step 6: Commit Trigger evidence**

```bash
git add docs/rollout-evidence/preview-YYYY-MM-DD.json
git commit -m "docs: record preview trigger runtime evidence"
```

---

## Phase 3: Mission Control production-path validation

### Task 4: Deploy Mission Control pointed at Ares, not Supabase

**Files:**
- Read: `apps/mission-control/src/lib/api.ts`
- Read: `apps/mission-control/src/lib/queryClient.ts`
- Evidence: `docs/rollout-evidence/preview-YYYY-MM-DD.json`

- [ ] **Step 1: Install frontend dependencies if missing**

```bash
npm --prefix apps/mission-control install
```

Expected: `apps/mission-control/node_modules/.bin/tsc` exists.

- [ ] **Step 2: Run Mission Control checks**

```bash
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
```

Expected: all commands exit 0.

- [ ] **Step 3: Configure deployed Mission Control runtime base URL**

```bash
VITE_RUNTIME_API_BASE_URL=https://<preview-ares>
```

- [ ] **Step 4: Deploy Mission Control**

Deploy the standalone Vite app to the preview/staging hosting target:

```bash
vercel deploy apps/mission-control \
  --yes \
  --build-env VITE_RUNTIME_API_BASE_URL=https://<preview-ares>
```

Expected: Vercel builds `apps/mission-control`, serves `dist`, and uses the app-level SPA rewrite for direct client-side route loads.

- [ ] **Step 5: Prove API source**

Open the deployed UI and verify dashboard/inbox/runs/tasks load from Ares API. Fixture fallback is acceptable in dev but not as production proof.

Expected evidence:

- Network requests hit `https://<preview-ares>/mission-control/...`.
- Responses have HTTP 200.
- UI shows runtime data created by prior smoke steps.

- [ ] **Step 6: Update evidence JSON**

Add:

```json
{
  "mission_control_url": "https://<preview-mission-control>",
  "mission_control_api_source": "passed"
}
```

- [ ] **Step 7: Commit Mission Control evidence**

```bash
git add docs/rollout-evidence/preview-YYYY-MM-DD.json
git commit -m "docs: record preview mission control evidence"
```

---

## Phase 4: Provider webhook and no-live smoke validation

### Task 5: Wire provider webhooks to preview/staging Ares

**Files:**
- Read: `docs/production-readiness-handoff.md`
- Read: `scripts/smoke_provider_readiness.py`
- Evidence: `docs/rollout-evidence/preview-YYYY-MM-DD.json`

- [ ] **Step 1: Configure webhook URLs**

Set provider webhook URLs:

```text
TextGrid inbound/status -> https://<preview-ares>/marketing/webhooks/textgrid
Cal.com booking        -> https://<preview-ares>/marketing/webhooks/calcom
Instantly webhook      -> https://<preview-ares>/lead-machine/webhooks/instantly
```

- [ ] **Step 2: Run provider request-shape smoke**

```bash
uv run python scripts/smoke_provider_readiness.py
```

Expected: exits 0 and does not send live traffic.

- [ ] **Step 3: Run no-live full-stack smoke**

```bash
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Expected: exits 0 and blocks any attempted live provider request.

- [ ] **Step 4: Verify Ares-visible results**

Confirm through API/Mission Control:

- dashboard loads
- runs exist
- lead/task state exists
- audit events exist
- usage events exist
- provider failure count does not hide failures

- [ ] **Step 5: Update evidence JSON**

Add:

```json
{
  "provider_webhooks_configured": "passed",
  "provider_request_shape_smoke": "passed",
  "no_live_smoke": "passed"
}
```

- [ ] **Step 6: Commit provider/no-live evidence**

```bash
git add docs/rollout-evidence/preview-YYYY-MM-DD.json
git commit -m "docs: record preview provider and no-live smoke evidence"
```

---

## Phase 5: Guarded live provider smoke

### Task 6: Send exactly controlled operator-owned test messages

**Files:**
- Use: `scripts/production_promotion_readiness.py`
- Use: `scripts/smoke_provider_readiness.py`
- Evidence: `docs/rollout-evidence/preview-YYYY-MM-DD.json`

- [ ] **Step 1: Confirm approved recipients**

Required variables:

```bash
ARES_SMOKE_SEND_SMS=1
ARES_SMOKE_TO_PHONE=<operator-owned-phone>
ARES_SMOKE_SEND_EMAIL=1
ARES_SMOKE_TO_EMAIL=<operator-owned-email>
```

- [ ] **Step 2: Run live provider smoke only with explicit flags**

Use the guarded smoke command documented in `docs/production-promotion.md` or the current provider readiness script’s live-send interface.

Expected:

- one SMS sent to approved phone
- one email sent to approved email
- provider IDs/statuses recorded
- Mission Control provider status exposes failures if any channel fails

- [ ] **Step 3: Update evidence JSON**

Add:

```json
{
  "live_provider_smoke": "passed",
  "live_provider_smoke_recipients": "operator-approved"
}
```

- [ ] **Step 4: Commit live provider evidence**

```bash
git add docs/rollout-evidence/preview-YYYY-MM-DD.json
git commit -m "docs: record preview live provider smoke evidence"
```

---

## Phase 6: Production promotion

### Task 7: Run production promotion gate before applying production changes

**Files:**
- Read: `docs/production-promotion.md`
- Use: `scripts/production_promotion_readiness.py`
- Use: `scripts/rollout_evidence.py`
- Evidence: `docs/rollout-evidence/production-YYYY-MM-DD.json`

- [ ] **Step 1: Create production backup/rollback reference**

Record a recoverable production backup, snapshot, release rollback ID, or equivalent rollback reference.

- [ ] **Step 2: Link production Supabase project**

```bash
supabase link --project-ref <production-project-ref>
```

Expected: `supabase/.temp/project-ref` contains `<production-project-ref>`.

- [ ] **Step 3: Run production readiness gate**

First validate the completed staging evidence:

```bash
uv run python scripts/rollout_evidence.py validate docs/rollout-evidence/preview-YYYY-MM-DD.json
```

Expected: `ready`. If it returns `blocked`, do not run production promotion.

```bash
uv run python scripts/production_promotion_readiness.py \
  --expected-project-ref <production-project-ref> \
  --expected-staging-project-ref <preview-project-ref> \
  --expected-staging-runtime-url https://<preview-ares> \
  --expected-staging-mission-control-url https://<preview-mission-control> \
  --staging-commit <commit-sha-proven-in-staging> \
  --staging-evidence-path docs/rollout-evidence/preview-YYYY-MM-DD.json \
  --backup-reference <backup-or-rollback-id> \
  --acknowledge-production \
  --run-linked-dry-run
```

Expected: readiness reports production promotion is allowed.

- [ ] **Step 4: Stop if any condition fails**

Do not apply migrations, deploy runtime, deploy Trigger, or send providers if the gate fails.

- [ ] **Step 5: Apply production migrations after gate passes**

```bash
supabase db push --linked
supabase migration list --linked
```

Expected: migrations apply to the verified production project only.

- [ ] **Step 6: Deploy production Ares, Trigger, and Mission Control from the staged commit**

Use the same commit SHA proven in staging. Configure production env with all runtime backends set to `supabase`.

- [ ] **Step 7: Run post-production smoke**

Verify:

```bash
curl -fsS https://<production-ares>/health
curl -fsS -H "Authorization: Bearer <runtime-key>" https://<production-ares>/hermes/tools
```

Then run no-live production-safe smoke and optional guarded live provider smoke.

- [ ] **Step 8: Create production evidence JSON**

Create `docs/rollout-evidence/production-YYYY-MM-DD.json`:

```json
{
  "ares_runtime_url": "https://<production-ares>",
  "commit": "<git-sha>",
  "environment": "production",
  "generated_at": "2026-04-25T00:00:00Z",
  "live_provider_smoke": "passed|not-run",
  "live_provider_smoke_recipients": "provided|not-run",
  "migration_apply": "passed",
  "migration_dry_run": "passed",
  "mission_control_api_source": "passed",
  "mission_control_url": "https://<production-mission-control>",
  "no_live_smoke": "passed",
  "operator_inputs_required": [
    "supabase_project_ref",
    "ares_runtime_url",
    "mission_control_url",
    "trigger_project_ref",
    "runtime_api_key_present",
    "supabase_service_role_key_present",
    "trigger_secret_key_present",
    "textgrid_status_callback_url",
    "provider_webhook_urls",
    "operator_owned_phone",
    "operator_owned_email"
  ],
  "operator_owned_email": "provided|not-run",
  "operator_owned_phone": "provided|not-run",
  "provider_request_shape_smoke": "passed",
  "provider_webhook_urls": {
    "calcom": "https://<production-ares>/marketing/webhooks/calcom",
    "instantly": "https://<production-ares>/lead-machine/webhooks/instantly",
    "textgrid": "https://<production-ares>/marketing/webhooks/textgrid"
  },
  "provider_webhooks_configured": "passed",
  "rollback_reference": "<backup-or-rollback-id>",
  "runtime_api_key_present": "yes",
  "runtime_auth": "passed",
  "runtime_health": "passed",
  "supabase_project_ref": "<production-project-ref>",
  "supabase_service_role_key_present": "yes",
  "textgrid_status_callback_url": "https://<production-ares>/marketing/webhooks/textgrid",
  "trigger_project_ref": "<trigger-ref>",
  "trigger_runtime_callbacks": "passed",
  "trigger_secret_key_present": "yes",
  "notes": []
}
```

- [ ] **Step 9: Commit production evidence**

```bash
git add docs/rollout-evidence/production-YYYY-MM-DD.json
git commit -m "docs: record production promotion evidence"
```

---

## Final production-ready acceptance gate

Run these from a clean checkout after production evidence exists:

```bash
git diff --check
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
uv run python scripts/smoke_provider_readiness.py
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Then manually verify hosted production:

- [ ] `https://<production-ares>/health` returns `{"status":"ok"}`.
- [ ] unauthenticated protected routes fail.
- [ ] authenticated protected routes pass.
- [ ] Mission Control hits Ares API source.
- [ ] Trigger lifecycle callbacks persist runs/events/artifacts.
- [ ] Supabase contains durable commands, approvals, runs, events, artifacts, leads, tasks, audit, usage, and provider receipt rows.
- [ ] Provider webhooks update Ares state.
- [ ] Rollback reference is still valid.

When every checkbox above has evidence, Ares can be called **fully wired and production ready** without a footnote the size of a cursed CVS receipt.
