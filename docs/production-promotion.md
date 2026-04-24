# Production Promotion

Phase 11 is a release gate, not an automatic deploy script. It must prove that production is receiving the exact commit already proven in staging, with a rollback point and an explicitly verified production Supabase target.

## Readiness Check

```bash
uv run python scripts/production_promotion_readiness.py \
  --expected-project-ref <production-project-ref> \
  --staging-commit <commit-sha-proven-in-staging> \
  --staging-evidence-path <path-to-staging-evidence-json> \
  --backup-reference <backup-or-rollback-id> \
  --acknowledge-production \
  --run-linked-dry-run
```

The command is read-only. It can run only:

- `supabase migration list --linked`
- `supabase db push --dry-run --linked`

It does not apply migrations, deploy Ares, deploy Trigger.dev, deploy Mission Control, or send provider traffic.

## Required Production Conditions

Production promotion stays blocked unless all are true:

- `supabase/.temp/project-ref` matches `--expected-project-ref`
- linked Supabase dry-run executes and passes
- current git commit equals `--staging-commit`
- `--staging-evidence-path` is valid JSON and contains the same commit under `commit`, `commit_sha`, `staging_commit`, `git.commit`, `git.commit_sha`, or `git.current_commit`
- `--backup-reference` is present
- `--acknowledge-production` is present
- production env vars are present
- all runtime backends are set to `supabase`

Required production env:

```bash
RUNTIME_API_KEY=...
CONTROL_PLANE_BACKEND=supabase
MARKETING_BACKEND=supabase
LEAD_MACHINE_BACKEND=supabase
SITE_EVENTS_BACKEND=supabase
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
TRIGGER_SECRET_KEY=...
TEXTGRID_ACCOUNT_SID=...
TEXTGRID_AUTH_TOKEN=...
TEXTGRID_FROM_NUMBER=...
TEXTGRID_STATUS_CALLBACK_URL=https://<production-runtime>/marketing/webhooks/textgrid
RESEND_API_KEY=...
RESEND_FROM_EMAIL=...
CAL_BOOKING_URL=...
```

## Promotion Order

After readiness reports `ready`:

1. Confirm backup/rollback reference is recoverable.
2. Apply the same migration chain proven in staging.
3. Deploy Ares runtime with Supabase-backed backends.
4. Deploy Trigger.dev jobs from the same commit.
5. Deploy Mission Control pointed at production Ares.
6. Run no-live-sends smoke against production-safe fixtures.
7. Run live SMS/email smoke only with explicit recipient flags.
8. Monitor command ingestion, approvals, Trigger callbacks, TextGrid status callbacks, Cal.com callbacks, Mission Control dashboard, audit, and usage.

## Live Provider Smoke

The readiness gate never enables live smoke unless both `--allow-live-provider-smoke` and recipient flags are present:

```bash
ARES_SMOKE_SEND_SMS=1 ARES_SMOKE_TO_PHONE=+15551234567 \
ARES_SMOKE_SEND_EMAIL=1 ARES_SMOKE_TO_EMAIL=operator@example.com \
uv run python scripts/production_promotion_readiness.py \
  --expected-project-ref <production-project-ref> \
  --staging-commit <commit-sha-proven-in-staging> \
  --staging-evidence-path <path-to-staging-evidence-json> \
  --backup-reference <backup-or-rollback-id> \
  --acknowledge-production \
  --allow-live-provider-smoke \
  --run-linked-dry-run
```

Run the provider request-shape check before any real send:

```bash
uv run python scripts/smoke_provider_readiness.py
```
