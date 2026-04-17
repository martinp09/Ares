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

## Initial Direction

- Generalist core first
- Industry packs second
- Real estate first
- Marketing control plane before seller-ops cutover

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

## Verification

- Python: `uv run pytest -q`
- Lead machine smoke: `uv run python scripts/smoke/lead_machine_smoke.py`
- Trigger.dev: `npx tsc -p trigger/tsconfig.json --noEmit`

## Bootstrap

- `make dev` prints the local Ares / Mission Control / Trigger bootstrap commands.
- `make smoke` runs the lead machine smoke harness.

## Source of Truth

- `CONTEXT.md` for quick session routing
- `memory.md` for indexed master memory
- future runtime database for canonical business state

## Trigger Setup

- Set `TRIGGER_PROJECT_REF` in `.env` before running Trigger commands.
