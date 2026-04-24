# Hermes, Ares, Trigger.dev, Supabase Runbook

Status: local development contract

## Ownership

- Hermes: operator shell, chat, approvals, summaries.
- Ares: FastAPI runtime, policy, provider adapters, Trigger callback ingestion, Mission Control read models.
- Trigger.dev: async jobs, retries, schedules, delays.
- Supabase: canonical durable state when a Supabase backend is explicitly enabled.
- Mission Control: Ares-backed operator UI.

## Local Environment

Use `.env.example` as the contract. For local development without Supabase, keep these defaults:

```bash
RUNTIME_API_BASE_URL=http://127.0.0.1:8000
RUNTIME_API_KEY=dev-runtime-key
CONTROL_PLANE_BACKEND=memory
MARKETING_BACKEND=memory
LEAD_MACHINE_BACKEND=memory
SITE_EVENTS_BACKEND=memory
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
VITE_RUNTIME_API_BASE_URL=
```

Enable Supabase only for a deliberate persistence slice with known project ref, service role key, and migration target.

## Startup

Terminal 1:

```bash
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
RUNTIME_API_BASE_URL=http://127.0.0.1:8000 \
RUNTIME_API_KEY=dev-runtime-key \
npm --prefix apps/mission-control run dev -- --host 127.0.0.1 --port 5173
```

Terminal 3:

```bash
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000 \
HERMES_RUNTIME_API_KEY=dev-runtime-key \
npm --prefix trigger run dev
```

## First Smoke

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -H 'Authorization: Bearer dev-runtime-key' \
  http://127.0.0.1:8000/hermes/tools
```

Expected:

- `/health` returns `{"status":"ok"}`.
- `/hermes/tools` returns the backend-owned Hermes tool list.

## Supabase Safety

Before any linked Supabase operation:

```bash
supabase migration list --linked
supabase db push --dry-run --linked
```

Local reset for Supabase implementation slices should use the machine-specific vector exclusion until the Colima mount issue is resolved:

```bash
supabase start -x vector
supabase db reset --local
supabase stop
colima stop
```

Do not run production migrations from an unverified checkout.
