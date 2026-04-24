# Ares

Enterprise agent platform and deterministic business runtime for Hermes dogfood.

Agents are the product unit. Mission Control is the operator cockpit.

Hermes is the always-on shell.
This repo is the deterministic runtime, policy layer, orchestration surface, and system-of-record integration layer that Hermes controls.

## Core Principles

- Hermes handles interaction, approvals, and coordination.
- This repo handles typed commands, business policy, provider adapters, and execution wiring.
- `memory.md` is the master memory file.
- `CONTEXT.md` is the short router and TODO file. Keep it under 50 lines and point to exact sections in `memory.md`.
- `WAT_Architecture.md` defines the operating model for workflows, agents, and tools.
- Hermes <-> Ares setup/runbook: `docs/hermes-ares-integration-runbook.md`
- Full-stack local runbook: `docs/hermes-ares-trigger-supabase-runbook.md`

## Initial Direction

- Generalist core first
- Industry packs second
- Real estate first
- Marketing control plane before seller-ops cutover

## Ares North Star

Ares is a self-hosted operating system for distressed real-estate lead management. It owns the data, automates the workflow, and surfaces only the decisions that require a human.

## Current Runtime Surface

- `GET /health`
- `POST /commands`
- `POST /approvals/{approval_id}/approve`
- `GET /runs/{run_id}`
- `POST /replays/{run_id}`
- `GET /hermes/tools`
- `POST /hermes/tools/{tool_name}/invoke`
- `POST /agents`
- `GET /agents/{agent_id}`
- `POST /agents/{agent_id}/revisions/{revision_id}/publish`
- `POST /agents/{agent_id}/revisions/{revision_id}/archive`
- `POST /agents/{agent_id}/revisions/{revision_id}/clone`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/events`
- `POST /permissions`
- `GET /permissions/{agent_revision_id}`
- `POST /outcomes`
- `POST /agent-assets`
- `GET /agent-assets/{asset_id}`
- `POST /agent-assets/{asset_id}/bind`
- `GET /mission-control/dashboard`
- `GET /mission-control/inbox`
- `GET /mission-control/runs`
- `POST /site-events`
- `POST /trigger/callbacks/runs/{run_id}/started`
- `POST /trigger/callbacks/runs/{run_id}/completed`
- `POST /trigger/callbacks/runs/{run_id}/failed`
- `POST /trigger/callbacks/runs/{run_id}/artifacts`

Current implementation notes:

- FastAPI runtime uses an in-memory control-plane store for now, with repository seams under `app/db/`
- Trigger.dev marketing worker chain is scaffolded under `trigger/`
- Trigger.dev is the current host infrastructure, not the platform identity
- Mission Control has native backend read models plus an `apps/mission-control/` cockpit scaffold
- The new Intake view fronts the fixture-backed happy path: submission -> appointment -> confirmation SMS -> reminder SMS
- Mission Control UI now follows the approved dark industrial terminal / pixel CRT style system
- site-event ingestion is append-only and non-blocking at the API layer
- Supabase remains the intended system of record, but live wiring is intentionally deferred in this slice

## Local Runtime Contract

Default local development stays memory-backed unless a Supabase slice is intentionally enabled:

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

Startup:

```bash
uv run --with uvicorn uvicorn app.main:app --host 127.0.0.1 --port 8000
RUNTIME_API_BASE_URL=http://127.0.0.1:8000 RUNTIME_API_KEY=dev-runtime-key npm --prefix apps/mission-control run dev -- --host 127.0.0.1 --port 5173
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000 HERMES_RUNTIME_API_KEY=dev-runtime-key npm --prefix trigger run dev
```

First smoke:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS -H 'Authorization: Bearer dev-runtime-key' http://127.0.0.1:8000/hermes/tools
```

## Verification

- Python: `uv run pytest -q`
- Lead machine smoke: `uv run python scripts/smoke/lead_machine_smoke.py`
- Trigger.dev: `npm --prefix trigger run typecheck`
- Mission Control: `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`

## Bootstrap

- `make dev` prints the local Ares / Mission Control / Trigger bootstrap commands.
- `make smoke` runs the lead machine smoke harness.

## Source of Truth

- `CONTEXT.md` for quick session routing
- `memory.md` for indexed master memory
- `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md` for the current cohesion integration scope
- `docs/superpowers/specs/2026-04-24-ares-full-stack-cohesion-spec.md` for the accepted boundary gate
- `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md` for the merged phased Ares implementation sequence
- `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json` as the overnight loop handoff artifact
- future runtime database for canonical business state

## Phase 1 Guardrails

- Counties remain fixed: Harris, Tarrant, Montgomery, Dallas, Travis
- Lead selection rule: probate first, tax delinquency as overlay
- Outreach rule: drafts stay pending human approval before any send

## Trigger Setup

- Set `TRIGGER_PROJECT_REF` in `.env` before running Trigger commands.
