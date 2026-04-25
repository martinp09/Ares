# Ares Production Readiness Handoff

Status: **test branch / readiness handoff**  
Branch: `test/production-readiness-handoff`  
Base commit: `0c14769` (`origin/main`)  
Updated: `2026-04-24T13:00:33Z`

## Plain-English status

Ares is now **wired in code** but **not yet proven live**.

The backend plumbing exists: FastAPI routes, Supabase adapters, Trigger runtime callbacks, Mission Control API clients, lead-machine flows, provider adapters, audit/usage, smoke scripts, and guarded readiness gates.

What has **not** happened yet is the live promotion step: linking a real Supabase project, applying migrations there, deploying Ares, deploying Trigger workers, pointing Mission Control at the deployed Ares API, wiring live provider webhooks, and proving the full loop with smoke evidence.

## What “fully wired and production ready” means

Ares is production ready only when this chain works against the real hosted environment:

```text
Hermes / Mission Control
  -> deployed Ares API
  -> Supabase-backed canonical state
  -> Trigger.dev jobs
  -> provider APIs + webhooks
  -> back into Ares
  -> visible in Mission Control, audit, usage, runs, tasks, and lead timelines
```

Local memory-backed tests are necessary but not enough. Production readiness requires live-environment evidence.

## Current code capabilities

The current `origin/main` contains these implemented/gated pieces:

1. **Runtime API**
   - FastAPI app includes commands, approvals, runs, replays, Hermes tools, agents, catalog installs, orgs, memberships, sessions, skills, permissions, RBAC, release management, secrets, audit, usage, outcomes, assets, Mission Control, site events, Trigger callbacks, marketing, lead machine, and Ares operator routes.

2. **Supabase persistence adapter**
   - `SupabaseControlPlaneClient.transaction()` hydrates and persists through `app/db/control_plane_store_supabase.py`.
   - Core runtime tables include commands, approvals, runs, events, artifacts.
   - Runtime text/snapshot tables include agents, revisions, sessions, turns, permissions, RBAC, secrets, audit, usage, outcomes, assets, Mission Control threads, skills, and host adapter dispatches.
   - Rollback/recovery logic snapshots and restores on failed flush.

3. **Trigger runtime contract**
   - Trigger jobs call Ares runtime endpoints.
   - Trigger lifecycle callbacks report started/completed/failed/artifacts back into Ares.
   - Trigger remains schedule/retry infrastructure, not the source of truth.

4. **Mission Control**
   - Mission Control frontend calls Ares runtime endpoints.
   - Backend exposes dashboard, inbox, runs, tasks, lead-machine, approvals, agents, assets, governance, secrets, audit, usage, provider status, outbound test sends, and turns.
   - Frontend still has fixture fallback behavior for dev/resilience; production validation must prove API source, not fixture source.

5. **Lead machine**
   - Canonical intake routes exist for generic lead intake and probate intake.
   - Marketing/lead-machine repositories support memory and Supabase-backed modes.
   - Provider failures create durable/manual-review surfaces visible in Mission Control.

6. **Provider integration surfaces**
   - TextGrid, Resend/email, Cal.com, Instantly-related runtime surfaces and readiness checks exist.
   - Live provider sends remain gated and require explicit opt-in recipients.

7. **Readiness gates**
   - Preview/staging readiness gate: `scripts/preview_rollout_readiness.py`
   - Production promotion gate: `scripts/production_promotion_readiness.py`
   - Full-stack no-live smoke: `scripts/smoke_full_stack_cohesion.py`
   - Provider request-shape smoke: `scripts/smoke_provider_readiness.py`

## Curative-title data workflow doctrine

The curative-title lead machine is **land-record-first**, not probate-first. Probate filings are useful party clues, but the decisive evidence is in deeds, affidavits, probate-related recordings, legal descriptions, grantor/grantee chains, and document images/details that reveal heirs, descendants, and partial-rights holders.

The browser harness / Hermes browser automation is a foundational method for this workflow because county portals are fragmented and often require faithful human-browser interaction before any reliable script can be built.

See: `docs/curative-title-data-pipeline.md`.

Wiki hub: `docs/curative-title-wiki/index.md`.

## What is still required

### Gate 1 — Choose and verify environments

Required environments:

- `preview` or `staging` Supabase project
- `production` Supabase project
- deployed Ares runtime target for preview/staging
- deployed Ares runtime target for production
- Trigger.dev project/environment
- Mission Control hosting target

Required evidence:

- Supabase project refs recorded in rollout evidence files.
- Ares base URLs recorded.
- Trigger project ref recorded.
- Mission Control URL recorded.
- Rollback/backup reference recorded before production promotion.

### Gate 2 — Apply Supabase migrations to preview/staging

Run from a clean checkout of this branch or a successor implementation branch:

```bash
supabase link --project-ref <preview-project-ref>
uv run python scripts/preview_rollout_readiness.py \
  --expected-project-ref <preview-project-ref> \
  --run-linked-dry-run
supabase db push --linked
supabase migration list --linked
```

Acceptance:

- Linked Supabase project ref matches the expected preview/staging ref.
- Dry run passes before apply.
- Migration apply completes.
- Migration list shows the expected chain.
- No production project is linked during preview work.

### Gate 3 — Deploy Ares preview/staging runtime

Ares must run with Supabase-backed backends:

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

Acceptance:

```bash
curl -fsS https://<preview-ares>/health
curl -fsS -H "Authorization: Bearer <runtime-key>" https://<preview-ares>/hermes/tools
```

Must prove:

- health route responds
- protected route rejects without auth
- protected route succeeds with auth
- Ares writes and reads Supabase state

### Gate 4 — Deploy Trigger workers against preview/staging Ares

Required env:

```bash
RUNTIME_API_BASE_URL=https://<preview-ares>
RUNTIME_API_KEY=<runtime-key>
TRIGGER_SECRET_KEY=<preview-trigger-secret>
```

Acceptance:

- Trigger lead-machine jobs call Ares endpoints.
- Trigger lifecycle callbacks update Ares runs.
- Ares persists run started/completed/failed/artifact events into Supabase-backed state.

### Gate 5 — Deploy Mission Control against preview/staging Ares

Mission Control must point at Ares, not Supabase:

```bash
VITE_RUNTIME_API_BASE_URL=https://<preview-ares>
```

Standalone Vercel deploy once the hosted Ares runtime URL exists:

```bash
vercel deploy apps/mission-control \
  --yes \
  --build-env VITE_RUNTIME_API_BASE_URL=https://<preview-ares>
```

Notes:

- `apps/mission-control/vercel.json` builds the standalone Vite app from `dist` and rewrites SPA deep links to `index.html`.
- Do not set a public `VITE_RUNTIME_API_KEY`; runtime authentication must stay server-side or in the Ares host/proxy layer.

Acceptance:

- Dashboard loads from API source.
- Inbox loads from API source.
- Runs load from API source.
- Tasks/lead actions mutate backend state.
- Fixture fallback is not mistaken for production success.

### Gate 6 — Wire provider webhooks without live sends

Configure provider webhook targets:

```text
TextGrid inbound/status -> https://<preview-ares>/marketing/webhooks/textgrid
Cal.com booking        -> https://<preview-ares>/marketing/webhooks/calcom
Instantly webhook      -> https://<preview-ares>/lead-machine/webhooks/instantly
```

Acceptance:

- Webhook secrets are configured where supported.
- A synthetic/test webhook creates provider receipt rows.
- Webhook handling updates lead/message/booking/task state.
- Mission Control shows the resulting state.

### Gate 7 — Run no-live full-stack smoke

Run against local first, then equivalent hosted smoke using preview/staging configuration.

Local command:

```bash
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Acceptance:

- command created
- run lifecycle updated
- lead intake works
- manual task created
- booking webhook works
- inbound SMS webhook works
- Mission Control dashboard/runs reflect state
- audit and usage entries exist
- no live provider request is sent

### Gate 8 — Run guarded live provider smoke

Only after no-live smoke passes and only to approved operator-owned recipients.

Required:

```bash
ARES_SMOKE_SEND_SMS=1
ARES_SMOKE_TO_PHONE=<operator-owned-phone>
ARES_SMOKE_SEND_EMAIL=1
ARES_SMOKE_TO_EMAIL=<operator-owned-email>
```

Acceptance:

- TextGrid sends one test SMS to the approved number.
- Resend/email sends one test email to the approved address.
- Status callbacks/webhooks are received or provider receipts are recorded.
- Message IDs/statuses appear in backend state.
- Mission Control provider status does not hide failures.

### Gate 9 — Promote the exact staged commit to production

Before production:

- staging evidence JSON exists
- production Supabase backup/rollback reference exists
- production env vars are present
- production project ref is verified
- production dry run passes

Command shape:

```bash
uv run python scripts/production_promotion_readiness.py \
  --expected-project-ref <production-project-ref> \
  --staging-commit <commit-sha-proven-in-staging> \
  --staging-evidence-path <path-to-staging-evidence-json> \
  --backup-reference <backup-or-rollback-id> \
  --acknowledge-production \
  --run-linked-dry-run
```

Acceptance:

- readiness reports ready
- migration dry-run passed against production-linked project
- HEAD equals staged commit
- staging evidence contains same commit
- backup reference is present
- all production runtime backends are set to `supabase`

### Gate 10 — Production post-promotion proof

After deploying production:

- `/health` passes
- protected auth works
- Mission Control loads API source
- Trigger callbacks work
- no-live production-safe smoke passes
- approved live SMS/email smoke passes if enabled
- Supabase rows exist for commands, runs, events, leads, tasks, audit, usage, provider receipts
- rollback path remains available

## Production-ready definition of done

Ares is fully wired and production ready only when all are true:

- [ ] Supabase preview/staging migrations applied and verified.
- [ ] Supabase production migration dry-run passed against verified production project.
- [ ] Ares preview/staging deployed with Supabase-backed backends.
- [ ] Ares production deployed with Supabase-backed backends.
- [ ] Trigger.dev workers deployed from the same tested commit.
- [ ] Mission Control deployed and pointed at Ares runtime, not Supabase.
- [ ] Provider webhooks point back to Ares.
- [ ] No-live smoke passes in hosted environment.
- [ ] Live provider smoke passes only with explicit approved recipients.
- [ ] Mission Control shows real API data and backend mutations.
- [ ] Supabase contains durable rows for commands/runs/leads/tasks/audit/usage/provider receipts.
- [ ] Production rollback/backup reference exists.
- [ ] Production evidence file records commit, env target refs, smoke outputs, and rollback reference.

## Do not do these

- Do not run production migrations from a machine linked to the wrong Supabase project.
- Do not let Mission Control call Supabase directly.
- Do not make Trigger.dev canonical state.
- Do not run live SMS/email smoke without explicit recipient flags.
- Do not use fixture-backed UI success as production proof.
- Do not deploy a commit to production that is different from the staged/evidenced commit.
- Do not remove `business_id + environment` while adding org-scoped behavior.

## Evidence files to create during rollout

Use these file paths for rollout artifacts. Keep secrets out of them.

```text
docs/rollout-evidence/preview-YYYY-MM-DD.json
docs/rollout-evidence/staging-YYYY-MM-DD.json
docs/rollout-evidence/production-YYYY-MM-DD.json
```

Create the preview/staging skeleton before Gate 1:

```bash
uv run python scripts/rollout_evidence.py init \
  docs/rollout-evidence/preview-YYYY-MM-DD.json \
  --environment preview \
  --commit "$(git rev-parse HEAD)"
```

Validate it after each gate update:

```bash
uv run python scripts/rollout_evidence.py validate \
  docs/rollout-evidence/preview-YYYY-MM-DD.json
```

The validator is expected to return `blocked` while any field is still `TODO`. That is intentional. Production promotion also rejects staging evidence that still has TODO fields, missing required fields, or secret env-var names copied into the JSON.

Each evidence file should include:

```json
{
  "ares_runtime_url": "https://<preview-ares>",
  "commit": "<git-sha>",
  "environment": "preview",
  "generated_at": "2026-04-25T00:00:00Z",
  "live_provider_smoke": "not-run",
  "live_provider_smoke_recipients": "not-run",
  "migration_apply": "passed",
  "migration_dry_run": "passed",
  "mission_control_api_source": "passed",
  "mission_control_url": "https://<preview-mission-control>",
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
    "calcom": "https://<preview-ares>/marketing/webhooks/calcom",
    "instantly": "https://<preview-ares>/lead-machine/webhooks/instantly",
    "textgrid": "https://<preview-ares>/marketing/webhooks/textgrid"
  },
  "provider_webhooks_configured": "passed",
  "rollback_reference": "not-required-for-preview",
  "runtime_api_key_present": "yes",
  "runtime_auth": "passed",
  "runtime_health": "passed",
  "supabase_project_ref": "<project-ref>",
  "supabase_service_role_key_present": "yes",
  "textgrid_status_callback_url": "https://<preview-ares>/marketing/webhooks/textgrid",
  "trigger_project_ref": "<trigger-ref>",
  "trigger_runtime_callbacks": "passed",
  "trigger_secret_key_present": "yes",
  "notes": []
}
```

Production promotion must also verify staging target identity:

```bash
uv run python scripts/production_promotion_readiness.py \
  --expected-project-ref <production-project-ref> \
  --expected-staging-project-ref <preview-project-ref> \
  --expected-staging-runtime-url https://<preview-ares> \
  --expected-staging-mission-control-url https://<preview-mission-control> \
  --staging-commit <git-sha> \
  --staging-evidence-path docs/rollout-evidence/preview-YYYY-MM-DD.json \
  --backup-reference <backup-or-release-id> \
  --acknowledge-production \
  --run-linked-dry-run
```

## Operator summary

This branch does not claim production readiness. It creates the handoff and checklist for proving it without lying to ourselves like clowns with a Kubernetes YAML addiction.
