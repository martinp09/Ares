# Ares Production Readiness Finish Today Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining live wiring gates so current `origin/main` can be honestly promoted to production today.

**Architecture:** Ares remains the deterministic runtime/API/state layer. Supabase is canonical persistence, Trigger.dev is async execution, providers own external delivery, and Mission Control reads Ares APIs only. Dashboard utility polish is explicitly out of scope for this plan.

**Tech Stack:** FastAPI, pytest, Supabase CLI/PostgREST, Trigger.dev, Vercel, React/Vite Mission Control, TextGrid, Resend, Cal.com, Instantly, shell smoke scripts.

---

## Current Baseline

- Repo: `/Users/solomartin/Projects/Ares`
- Baseline branch: `main`
- Baseline commit: `902570240f777e9be0c16db59927042d16a48755`
- Existing preview evidence: `docs/rollout-evidence/preview-2026-04-25.json`
- Existing preview evidence commit: `abd2373`, so preview must be re-proven for `9025702` before production promotion.
- Known remaining blockers:
  - provider webhooks are not configured/proven against hosted Ares
  - hosted live provider smoke lacks explicit operator-owned phone/email evidence
  - production backup/rollback reference is missing
  - production evidence JSON is missing

## File Structure

- Modify: `docs/rollout-evidence/preview-2026-04-25.json`
  - Records re-proved preview evidence for commit `9025702`.
- Create: `docs/rollout-evidence/production-2026-04-25.json`
  - Records production promotion evidence and rollback reference.
- Modify: `CONTEXT.md`
  - Keep under 50 lines; update only after production evidence is complete.
- Modify: `TODO.md`
  - Mark completed production readiness gates and leave only true follow-up work.
- Modify: `memory.md`
  - Append a concise change-log entry with commit, evidence files, and final status.
- Use only: `scripts/rollout_evidence.py`
- Use only: `scripts/preview_rollout_readiness.py`
- Use only: `scripts/production_promotion_readiness.py`
- Use only: `scripts/smoke_provider_readiness.py`
- Use only: `scripts/smoke_full_stack_cohesion.py`

## Required Operator Inputs

Do not begin the live/provider/production phases until these are available:

- Preview Ares runtime URL for commit `9025702`.
- Preview Mission Control URL for commit `9025702`.
- Preview Supabase project ref. Existing candidate: `awmsrjeawcxndfnggoxw`.
- Production Supabase project ref.
- Production Ares runtime target and Mission Control target.
- Trigger.dev project/environment to deploy against. Current project: `proj_puouljyhwiraonjkpiki`.
- Runtime API keys present in the target hosts. Do not commit values.
- Supabase service role keys present in the target hosts. Do not commit values.
- Trigger secret key present in the target hosts. Do not commit values.
- TextGrid account SID/auth token/from number available in runtime env. Do not commit values.
- Resend API key/from email available in runtime env. Do not commit values.
- Cal.com booking URL/webhook access.
- Instantly webhook access if cold outbound is in scope today.
- Explicit operator-owned phone number for live SMS smoke.
- Explicit operator-owned email for live email smoke.
- Recoverable production rollback/backup reference before production promotion.

## Chunk 1: Re-Prove Preview On Current Main

### Task 1: Validate local baseline

**Files:**
- Read: `CONTEXT.md`
- Read: `TODO.md`
- Read: `docs/rollout-evidence/preview-2026-04-25.json`

- [ ] **Step 1: Confirm clean current main**

Run:

```bash
git fetch origin main:refs/remotes/origin/main
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

Expected: checkout is clean and `HEAD` equals `origin/main`.

- [ ] **Step 2: Run code verification before redeploy**

Run:

```bash
git diff --check
uv lock --check
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
uv run python scripts/smoke_provider_readiness.py
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Expected: all commands exit 0. If any fail, fix with focused tests before touching hosted targets.

### Task 2: Re-deploy preview/staging from current commit

**Files:**
- Modify: `docs/rollout-evidence/preview-2026-04-25.json`
- Use: `scripts/preview_rollout_readiness.py`
- Use: `scripts/rollout_evidence.py`

- [ ] **Step 1: Verify preview Supabase target**

Run:

```bash
supabase link --project-ref <preview-project-ref>
uv run python scripts/preview_rollout_readiness.py \
  --expected-project-ref <preview-project-ref> \
  --run-linked-dry-run
```

Expected: linked ref matches, dry-run passes, no production project is linked.

- [ ] **Step 2: Apply preview migrations only if needed**

Run:

```bash
supabase db push --linked
supabase migration list --linked
```

Expected: migration chain is current and still targets preview/staging.

- [ ] **Step 3: Deploy Ares preview from `9025702`**

Configure preview env:

```bash
RUNTIME_API_KEY=<preview-runtime-key>
CONTROL_PLANE_BACKEND=supabase
MARKETING_BACKEND=supabase
LEAD_MACHINE_BACKEND=supabase
SITE_EVENTS_BACKEND=supabase
SUPABASE_URL=<preview-supabase-url>
SUPABASE_SERVICE_ROLE_KEY=<preview-service-role-key>
TRIGGER_SECRET_KEY=<preview-trigger-secret>
TEXTGRID_STATUS_CALLBACK_URL=https://<preview-ares>/marketing/webhooks/textgrid
```

Expected: deployed Ares URL is known and records commit `9025702`.

- [ ] **Step 4: Prove preview Ares runtime**

Run:

```bash
curl -fsS https://<preview-ares>/health
curl -i https://<preview-ares>/hermes/tools
curl -fsS -H "Authorization: Bearer <runtime-key>" https://<preview-ares>/hermes/tools
```

Expected: health passes, unauthenticated protected route fails, authenticated route passes.

- [ ] **Step 5: Deploy Mission Control preview pointed at preview Ares**

Run:

```bash
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
vercel deploy apps/mission-control \
  --yes \
  --build-env VITE_RUNTIME_API_BASE_URL=https://<preview-ares>
```

Expected: deployed Mission Control URL is known and its built bundle points at preview Ares.

- [ ] **Step 6: Deploy or sync Trigger runtime callback env**

Run:

```bash
npm --prefix trigger run typecheck
```

Then deploy/sync Trigger with:

```bash
RUNTIME_API_BASE_URL=https://<preview-ares>
RUNTIME_API_KEY=<runtime-key>
TRIGGER_SECRET_KEY=<preview-trigger-secret>
```

Expected: Trigger worker version is recorded and callback env targets preview Ares.

- [ ] **Step 7: Update preview evidence for current commit**

Patch `docs/rollout-evidence/preview-2026-04-25.json`:

```json
{
  "commit": "902570240f777e9be0c16db59927042d16a48755",
  "supabase_project_ref": "<preview-project-ref>",
  "ares_runtime_url": "https://<preview-ares>",
  "mission_control_url": "https://<preview-mission-control>",
  "trigger_project_ref": "<trigger-project-ref>",
  "migration_dry_run": "passed:<details>",
  "migration_apply": "passed:<details>",
  "runtime_health": "passed:<details>",
  "runtime_auth": "passed:<details>",
  "trigger_runtime_callbacks": "passed:<details>",
  "mission_control_api_source": "passed:<details>"
}
```

Do not include secret values or secret variable names.

## Chunk 2: Provider Webhooks And Hosted No-Live Proof

### Task 3: Configure provider webhooks to preview Ares

**Files:**
- Modify: `docs/rollout-evidence/preview-2026-04-25.json`
- Use: `scripts/smoke_provider_readiness.py`
- Use: `scripts/smoke_full_stack_cohesion.py`

- [ ] **Step 1: Configure provider URLs**

Set:

```text
TextGrid inbound/status -> https://<preview-ares>/marketing/webhooks/textgrid
Cal.com booking        -> https://<preview-ares>/marketing/webhooks/calcom
Instantly webhook      -> https://<preview-ares>/lead-machine/webhooks/instantly
```

Expected: provider dashboards show those URLs. Record only URLs and status, not secrets.

- [ ] **Step 2: Run provider request-shape smoke**

Run:

```bash
uv run python scripts/smoke_provider_readiness.py
```

Expected: exits 0, `live_sms_requested=false`, `live_email_requested=false`.

- [ ] **Step 3: Run no-live full-stack smoke**

Run:

```bash
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Expected: exits 0, no live provider request is sent.

- [ ] **Step 4: Prove hosted webhook receipts**

Send provider-supported test/synthetic webhooks to preview Ares:

```bash
curl -fsS -H "Authorization: Bearer <runtime-key>" \
  https://<preview-ares>/mission-control/dashboard
```

Expected: Ares records provider receipt/state updates and Mission Control read models show resulting lead/message/booking/task state.

- [ ] **Step 5: Update preview evidence**

Patch:

```json
{
  "provider_webhooks_configured": "passed:<provider-dashboard-or-test-details>",
  "provider_request_shape_smoke": "passed:shape-only-no-live",
  "no_live_smoke": "passed:<local-or-hosted-details>"
}
```

## Chunk 3: Guarded Live Provider Smoke

### Task 4: Run exactly controlled live SMS/email smoke

**Files:**
- Modify: `docs/rollout-evidence/preview-2026-04-25.json`
- Use: `scripts/smoke_provider_readiness.py`

- [ ] **Step 1: Confirm operator-owned recipients**

Record in working notes only:

```bash
ARES_SMOKE_TO_PHONE=<operator-owned-phone>
ARES_SMOKE_TO_EMAIL=<operator-owned-email>
```

Expected: user explicitly approves both values for live smoke today.

- [ ] **Step 2: Confirm live flags are explicit**

Run only after approval:

```bash
ARES_SMOKE_SEND_SMS=1 \
ARES_SMOKE_TO_PHONE=<operator-owned-phone> \
ARES_SMOKE_SEND_EMAIL=1 \
ARES_SMOKE_TO_EMAIL=<operator-owned-email> \
uv run python scripts/smoke_provider_readiness.py --allow-live
```

Expected: script reports live request intent and request shape. If the script still only builds request shapes, use the hosted Ares live-send endpoints already proven by local evidence and record provider IDs.

- [ ] **Step 3: Verify provider and Ares evidence**

Expected:

- exactly one SMS to approved phone
- exactly one email to approved email
- provider IDs/statuses captured
- TextGrid status callback reaches Ares
- Resend acceptance/failure reaches Ares or Mission Control provider status
- Mission Control surfaces provider failures instead of hiding them

- [ ] **Step 4: Update preview evidence**

Patch:

```json
{
  "live_provider_smoke": "passed:<sms-provider-id>,<email-provider-id>",
  "live_provider_smoke_recipients": "operator-approved",
  "operator_owned_phone": "provided",
  "operator_owned_email": "provided"
}
```

- [ ] **Step 5: Validate preview evidence is ready**

Run:

```bash
uv run python scripts/rollout_evidence.py validate docs/rollout-evidence/preview-2026-04-25.json
```

Expected: `status` is `ready`. If blocked, clear every `todo_fields` entry before production.

## Chunk 4: Production Promotion

### Task 5: Run production gate before applying production changes

**Files:**
- Create: `docs/rollout-evidence/production-2026-04-25.json`
- Use: `scripts/production_promotion_readiness.py`
- Use: `scripts/rollout_evidence.py`

- [ ] **Step 1: Create production rollback/backup reference**

Record a recoverable reference:

```text
rollback_reference=<backup-id-or-release-rollback-id>
```

Expected: reference can be used to recover production state or redeploy previous known-good runtime.

- [ ] **Step 2: Link production Supabase project**

Run:

```bash
supabase link --project-ref <production-project-ref>
cat supabase/.temp/project-ref
```

Expected: output equals `<production-project-ref>`.

- [ ] **Step 3: Run production promotion readiness**

Run:

```bash
uv run python scripts/production_promotion_readiness.py \
  --expected-project-ref <production-project-ref> \
  --expected-staging-project-ref <preview-project-ref> \
  --expected-staging-runtime-url https://<preview-ares> \
  --expected-staging-mission-control-url https://<preview-mission-control> \
  --staging-commit 902570240f777e9be0c16db59927042d16a48755 \
  --staging-evidence-path docs/rollout-evidence/preview-2026-04-25.json \
  --backup-reference <backup-or-rollback-id> \
  --acknowledge-production \
  --run-linked-dry-run
```

Expected: `status` is `ready`. If blocked, stop and fix the named blocker.

- [ ] **Step 4: Apply production migrations**

Run only after readiness returns `ready`:

```bash
supabase db push --linked
supabase migration list --linked
```

Expected: migrations apply to verified production project only.

- [ ] **Step 5: Deploy production Ares from exact commit**

Production env must include:

```bash
RUNTIME_API_KEY=<production-runtime-key>
CONTROL_PLANE_BACKEND=supabase
MARKETING_BACKEND=supabase
LEAD_MACHINE_BACKEND=supabase
SITE_EVENTS_BACKEND=supabase
SUPABASE_URL=<production-supabase-url>
SUPABASE_SERVICE_ROLE_KEY=<production-service-role-key>
TRIGGER_SECRET_KEY=<production-trigger-secret>
TEXTGRID_STATUS_CALLBACK_URL=https://<production-ares>/marketing/webhooks/textgrid
```

Expected: deployed runtime commit equals `9025702`.

- [ ] **Step 6: Deploy production Trigger and Mission Control**

Trigger:

```bash
RUNTIME_API_BASE_URL=https://<production-ares>
RUNTIME_API_KEY=<production-runtime-key>
TRIGGER_SECRET_KEY=<production-trigger-secret>
```

Mission Control:

```bash
vercel deploy apps/mission-control \
  --prod \
  --yes \
  --build-env VITE_RUNTIME_API_BASE_URL=https://<production-ares>
```

Expected: Mission Control points at production Ares and never calls Supabase directly.

- [ ] **Step 7: Run production-safe smoke**

Run:

```bash
curl -fsS https://<production-ares>/health
curl -i https://<production-ares>/hermes/tools
curl -fsS -H "Authorization: Bearer <runtime-key>" https://<production-ares>/hermes/tools
uv run python scripts/smoke_provider_readiness.py
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Expected: health passes, auth contract passes, provider shape passes, no-live smoke passes.

- [ ] **Step 8: Create production evidence JSON**

Run:

```bash
uv run python scripts/rollout_evidence.py init \
  docs/rollout-evidence/production-2026-04-25.json \
  --environment production \
  --commit 902570240f777e9be0c16db59927042d16a48755
```

Patch every field with production results:

```json
{
  "commit": "902570240f777e9be0c16db59927042d16a48755",
  "environment": "production",
  "supabase_project_ref": "<production-project-ref>",
  "ares_runtime_url": "https://<production-ares>",
  "mission_control_url": "https://<production-mission-control>",
  "trigger_project_ref": "<trigger-project-ref>",
  "runtime_api_key_present": "yes",
  "supabase_service_role_key_present": "yes",
  "trigger_secret_key_present": "yes",
  "textgrid_status_callback_url": "https://<production-ares>/marketing/webhooks/textgrid",
  "provider_webhook_urls": {
    "textgrid": "https://<production-ares>/marketing/webhooks/textgrid",
    "calcom": "https://<production-ares>/marketing/webhooks/calcom",
    "instantly": "https://<production-ares>/lead-machine/webhooks/instantly"
  },
  "migration_dry_run": "passed:<details>",
  "migration_apply": "passed:<details>",
  "runtime_health": "passed:<details>",
  "runtime_auth": "passed:<details>",
  "trigger_runtime_callbacks": "passed:<details>",
  "mission_control_api_source": "passed:<details>",
  "provider_webhooks_configured": "passed:<details>",
  "provider_request_shape_smoke": "passed:shape-only-no-live",
  "no_live_smoke": "passed:<details>",
  "live_provider_smoke": "passed|not-run:<details>",
  "live_provider_smoke_recipients": "operator-approved|not-run",
  "operator_owned_phone": "provided|not-run",
  "operator_owned_email": "provided|not-run",
  "rollback_reference": "<backup-or-rollback-id>",
  "notes": []
}
```

- [ ] **Step 9: Validate production evidence**

Run:

```bash
uv run python scripts/rollout_evidence.py validate docs/rollout-evidence/production-2026-04-25.json
```

Expected: `status` is `ready`.

## Chunk 5: Closeout

### Task 6: Update router docs and commit

**Files:**
- Modify: `CONTEXT.md`
- Modify: `TODO.md`
- Modify: `memory.md`
- Modify: `docs/rollout-evidence/preview-2026-04-25.json`
- Create: `docs/rollout-evidence/production-2026-04-25.json`

- [ ] **Step 1: Update `CONTEXT.md`**

Keep it under 50 lines. It must state:

- current branch and commit
- production evidence file path
- production-ready status
- any remaining explicit follow-up

- [ ] **Step 2: Update `TODO.md`**

Mark completed gates and leave only post-production/dashboard follow-up. Do not leave stale blocker text.

- [ ] **Step 3: Update `memory.md`**

Append a concise change-log entry with:

- preview evidence result
- production evidence result
- production project ref
- rollback reference
- verification commands
- final deployed URLs

- [ ] **Step 4: Final verification**

Run:

```bash
git diff --check
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
uv run python scripts/rollout_evidence.py validate docs/rollout-evidence/preview-2026-04-25.json
uv run python scripts/rollout_evidence.py validate docs/rollout-evidence/production-2026-04-25.json
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

Run:

```bash
git add CONTEXT.md TODO.md memory.md docs/rollout-evidence/preview-2026-04-25.json docs/rollout-evidence/production-2026-04-25.json
git commit -m "Record production readiness evidence"
```

- [ ] **Step 6: Shutdown resources**

Confirm no leftover local processes:

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P || true
lsof -iTCP:5173 -sTCP:LISTEN -n -P || true
```

Confirm any browser/dev/server processes started during execution are closed.

## Definition Of Done Today

- Preview evidence validates `ready` for commit `9025702`.
- Production promotion readiness reports `ready` before production changes.
- Production Supabase migrations applied only to verified production ref.
- Production Ares, Trigger, and Mission Control are deployed from commit `9025702`.
- Provider webhooks round-trip into Ares.
- Guarded live provider smoke is either passed with approved recipients or explicitly deferred with production evidence marking it `not-run` only if the operator chooses no live smoke today.
- Production evidence validates `ready`.
- Router docs reflect current truth.
- No dev servers, browser sessions, MCP sessions, or local long-running processes are left open.
