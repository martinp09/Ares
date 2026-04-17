---
title: "Hermes <-> Ares Integration Runbook"
status: draft
updated_at: "2026-04-17T14:44:47Z"
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

## Local development setup

### 1) Start Ares

From the repo root:

```bash
uv sync
```

Then run the FastAPI app with whatever ASGI runner exists in your environment, pointed at:

```text
app.main:app
```

A plain local example looks like this if `uvicorn` is available:

```bash
uvicorn app.main:app --reload --port 8000
```

### 2) Start the Mission Control UI

```bash
npm --prefix apps/mission-control install
npm --prefix apps/mission-control run dev
```

### 3) Start the Trigger worker

```bash
npm --prefix trigger install
npm --prefix trigger run dev
```

### 4) Point Hermes at Ares

On the Hermes side, set the connector to the Ares runtime URL and key:

```bash
export HERMES_RUNTIME_API_BASE_URL=http://localhost:8000
export HERMES_RUNTIME_API_KEY=dev-runtime-key
```

If you use Hermes profiles, put those values in the profile config or the profile env file used by that Hermes instance.

If Hermes is running as a gateway or CLI on another machine, point it at the Ares host instead of localhost.

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
