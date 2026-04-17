---
title: "Hermes <-> Ares Integration Runbook"
status: draft
updated_at: "2026-04-17T14:58:00Z"
---

# Hermes <-> Ares Integration Runbook

## What this is

Hermes is the operator shell.
Ares is the runtime Hermes points at.

You do **not** install Ares inside Hermes Agent.
You run Ares as a separate service and configure Hermes to call Ares over HTTP.

That is the boundary. Keep it that way or the stack turns into a haunted Blender of bad assumptions.

## Responsibility split

### Hermes owns

- chat and conversation
- approvals and operator interaction
- browsing and research
- human-facing coordination
- choosing *what* should happen next

### Ares owns

- typed commands
- business policy
- execution wiring
- runtime state and replay safety
- Mission Control read models
- Trigger.dev jobs
- provider adapters
- durable business state when the backend is live

### Providers own

- message transport
- webhook delivery
- third-party side effects

Providers are never the source of truth.

## Integration model

The live integration is a thin API boundary:

```text
Human
  -> Hermes
  -> Hermes-side tool / adapter / profile config
  -> Ares HTTP API
  -> jobs / DB / providers
  <- result back to Hermes
```

The important bit is this:

- Hermes does **not** contain the business logic
- Ares does **not** contain the chat shell
- Hermes just points at Ares

## Current Ares-side API surface

These are the runtime endpoints Hermes can hit:

- `GET /health`
- `POST /commands`
- `POST /approvals/{approval_id}/approve`
- `GET /runs/{run_id}`
- `POST /replays/{run_id}`
- `GET /hermes/tools`
- `POST /hermes/tools/{tool_name}/invoke`
- `GET /mission-control/dashboard`
- `GET /mission-control/inbox`
- `GET /mission-control/runs`
- `POST /trigger/callbacks/runs/{run_id}/started`
- `POST /trigger/callbacks/runs/{run_id}/completed`
- `POST /trigger/callbacks/runs/{run_id}/failed`
- `POST /trigger/callbacks/runs/{run_id}/artifacts`

## What gets installed where

### On the Hermes machine

Install Hermes Agent normally.
That host should contain:

- Hermes CLI / gateway / profile config
- Hermes memory and skills
- the connector config that points to Ares

Do **not** copy Ares business logic into Hermes skills.
A skill can call Ares, but it should not reimplement Ares.

### On the Ares machine

Run Ares as its own service.
That host should contain:

- the FastAPI runtime
- the Mission Control backend and UI
- Trigger.dev worker config
- provider credentials
- backend persistence config

## Required environment variables

### Ares runtime / API

These are the core Ares settings:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `LEAD_MACHINE_SUPABASE_URL`
- `LEAD_MACHINE_SUPABASE_SERVICE_ROLE_KEY`
- `TRIGGER_API_URL`
- `TRIGGER_SECRET_KEY`
- `TRIGGER_PROJECT_REF`
- `INSTANTLY_API_KEY`
- `INSTANTLY_WEBHOOK_SECRET`
- `TEXTGRID_ACCOUNT_SID`
- `TEXTGRID_AUTH_TOKEN`
- `TEXTGRID_FROM_NUMBER`
- `TEXTGRID_WEBHOOK_SECRET`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `CAL_API_KEY`
- `CAL_BOOKING_URL`
- `CAL_WEBHOOK_SECRET`

### Hermes -> Ares connector

These are the values the Hermes-side connector must know:

- `HERMES_RUNTIME_API_BASE_URL`
- `HERMES_RUNTIME_API_KEY`

The code already supports fallbacks to the non-HERMES names:

- `RUNTIME_API_BASE_URL`
- `RUNTIME_API_KEY`

### Trigger worker API client

The Trigger worker uses the same runtime pointer:

- `HERMES_RUNTIME_API_BASE_URL` or `RUNTIME_API_BASE_URL`
- `HERMES_RUNTIME_API_KEY` or `RUNTIME_API_KEY`

That is wired in `trigger/src/shared/runtimeApi.ts`.

## Hermes connector example

### Option 1: launch Hermes with explicit env vars

This is the simplest and least magical setup.

```bash
HERMES_RUNTIME_API_BASE_URL=http://10.0.0.25:8000 \
HERMES_RUNTIME_API_KEY=dev-runtime-key \
hermes -p ares-lab
```

Use the real Ares host IP or DNS name instead of `10.0.0.25`.
If Hermes is running on the same machine as Ares, `http://localhost:8000` is fine.

### Option 2: wrapper script for a named Hermes entrypoint

If you want a dedicated launcher instead of typing env vars every time:

```bash
#!/usr/bin/env bash
set -euo pipefail

export HERMES_RUNTIME_API_BASE_URL="${HERMES_RUNTIME_API_BASE_URL:-http://10.0.0.25:8000}"
export HERMES_RUNTIME_API_KEY="${HERMES_RUNTIME_API_KEY:-dev-runtime-key}"

exec hermes -p ares-lab "$@"
```

Save that as something like `~/bin/hermes-ares`, make it executable, and use it as your normal Hermes command.

### Option 3: profile-specific environment file

If your Hermes install keeps per-profile env files, put the same two variables there:

```bash
HERMES_RUNTIME_API_BASE_URL=http://10.0.0.25:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
```

That keeps the integration isolated to the `ares-lab` profile instead of leaking into every Hermes session.

## Copy/paste setups

### 1) Local dev on one machine

Use one terminal for each process.

Terminal 1 — Ares API:

```bash
cd /path/to/Ares
uv sync
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — Mission Control UI:

```bash
cd /path/to/Ares
npm --prefix apps/mission-control install
npm --prefix apps/mission-control run dev
```

Terminal 3 — Trigger worker:

```bash
cd /path/to/Ares
npm --prefix trigger install
npm --prefix trigger run dev
```

Terminal 4 — Hermes shell:

```bash
export HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
export HERMES_RUNTIME_API_KEY=dev-runtime-key
hermes -p ares-lab
```

### 2) Hermes gateway service on the operator box

Use this when Hermes is your always-on shell and Ares lives on a different machine.

```bash
export HERMES_RUNTIME_API_BASE_URL=http://10.0.0.25:8000
export HERMES_RUNTIME_API_KEY=dev-runtime-key
hermes -p ares-lab gateway install
hermes -p ares-lab gateway start
hermes -p ares-lab gateway status
```

Replace `10.0.0.25` with the real Ares host IP or DNS name.

### 3) Production host

Use the same pattern with real secrets and the production Ares URL.

```bash
export HERMES_RUNTIME_API_BASE_URL=https://ares.yourdomain.com
export HERMES_RUNTIME_API_KEY=replace-with-real-runtime-key
hermes -p ares-prod gateway install
hermes -p ares-prod gateway start
hermes -p ares-prod gateway status
```

If you prefer a wrapper script, keep those same two env vars in the script instead of your shell.

## First smoke test

### Check Ares health

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

### Check Hermes tool discovery

```bash
curl -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" \
  http://localhost:8000/hermes/tools
```

Expected:
- a JSON list of available Hermes tools
- no 401/403

### Send a sample command

```bash
curl -X POST http://localhost:8000/commands \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" \
  -d '{
    "business_id": "limitless",
    "environment": "dev",
    "command_type": "run_market_research",
    "idempotency_key": "cmd-001",
    "payload": {"topic": "houston tired landlords"}
  }'
```

Expected:
- `201` for a fresh command
- `200` for a deduped repeat
- a response body with `policy`, `status`, and either `run_id` or `approval_id`

## How Hermes should use it day to day

### Research / intake

Hermes gathers the messy input and then calls Ares with a typed command.

Example flow:

```text
Hermes reads lead / filing / listing / reply
  -> decides the command type
  -> POST /commands
  -> Ares queues or executes the work
  -> Hermes watches run status or approvals
```

### Approval flows

When Ares says approval is required:

```text
Hermes shows the approval to the user
  -> user approves in Hermes
  -> Hermes calls POST /approvals/{approval_id}/approve
  -> Ares continues the run
```

### Replay / recovery

If a run needs replaying:

```text
Hermes identifies the run
  -> POST /replays/{run_id}
  -> Ares reconstructs the run safely
```

### Mission Control reads

Hermes can display operator state from Ares read models:

- dashboard counts
- inbox threads
- run lineage
- lead-machine or marketing workspaces

## What not to do

- Do not copy Ares business logic into Hermes skills.
- Do not make Hermes the canonical database.
- Do not add a second queue just because it feels industrious.
- Do not let provider APIs become the source of truth.
- Do not bury the connector inside a random helper script with no env docs.

## Practical rule

If the action changes business state, Ares owns it.
If the action is operator conversation or judgment, Hermes owns it.
If the action is delayed or retried, Trigger.dev owns it.
If the action needs to survive, Supabase owns it when live.

## Minimum viable setup

To get the system moving, you need only this:

1. Hermes installed on the operator machine
2. Ares running as a separate API service
3. Hermes pointed at Ares with `HERMES_RUNTIME_API_BASE_URL` and `HERMES_RUNTIME_API_KEY`
4. Trigger.dev configured with the same runtime pointer
5. The required provider keys loaded in `.env`

That is the real setup.
Everything else is garnish unless a specific workflow proves it needs more.
