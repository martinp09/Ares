# Preview/Staging Rollout

Phase 10 is a hosted proof gate. It must verify a preview or staging target before any migration, deploy, Trigger worker, or live provider smoke.

## Readiness Check

```bash
uv run python scripts/preview_rollout_readiness.py --expected-project-ref <preview-project-ref>
```

This is read-only. It reports:

- linked Supabase project ref from `supabase/.temp/project-ref`
- required preview env var presence
- backend env selection
- required CLI availability
- whether preview migrations and no-live smoke are allowed

To run the linked Supabase read/dry-run gate after the project ref is verified:

```bash
uv run python scripts/preview_rollout_readiness.py \
  --expected-project-ref <preview-project-ref> \
  --run-linked-dry-run
```

The dry-run command executes only when the linked target matches the expected project ref.

## Required Preview Env

Preview/staging must set:

```bash
RUNTIME_API_KEY=...
CONTROL_PLANE_BACKEND=supabase
MARKETING_BACKEND=supabase
LEAD_MACHINE_BACKEND=supabase
SITE_EVENTS_BACKEND=supabase
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
TRIGGER_SECRET_KEY=...
```

Provider shape env for smoke readiness:

```bash
TEXTGRID_ACCOUNT_SID=...
TEXTGRID_AUTH_TOKEN=...
TEXTGRID_FROM_NUMBER=...
TEXTGRID_STATUS_CALLBACK_URL=https://<preview-runtime>/marketing/webhooks/textgrid
RESEND_API_KEY=...
RESEND_FROM_EMAIL=...
CAL_BOOKING_URL=...
```

## Hosted Gate

Run in this order:

```bash
uv run pytest -q
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npm --prefix trigger run typecheck
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

Then verify the linked target:

```bash
supabase migration list --linked
supabase db push --dry-run --linked
```

Apply preview migrations only after the readiness script reports `ready` and the linked dry-run is green.

## Live Provider Smoke

Do not run live provider smoke as part of default preview rollout. It requires explicit operator recipient flags:

```bash
ARES_SMOKE_SEND_SMS=1 ARES_SMOKE_TO_PHONE=+15551234567 \
  uv run python scripts/smoke_provider_readiness.py --allow-live

ARES_SMOKE_SEND_EMAIL=1 ARES_SMOKE_TO_EMAIL=operator@example.com \
  uv run python scripts/smoke_provider_readiness.py --allow-live
```

The default full-stack smoke remains no-live-sends only.
