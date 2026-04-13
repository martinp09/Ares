# Hermes Central Command

Reusable business runtime for a live Hermes agent deployment.

Hermes is the always-on shell.
This repo is the deterministic runtime, policy layer, orchestration surface, and system-of-record integration layer that Hermes controls.

## Core Principles

- Hermes handles interaction, approvals, and coordination.
- This repo handles typed commands, business policy, provider adapters, and execution wiring.
- `memory.md` is the master memory file.
- `CONTEXT.md` is the short router and TODO file. Keep it under 50 lines and point to exact sections in `memory.md`.
- `WAT_Architecture.md` defines the operating model for workflows, agents, and tools.

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
- `POST /site-events`

Current implementation notes:

- FastAPI runtime uses an in-memory control-plane store for now
- Trigger.dev marketing worker chain is scaffolded under `trigger/`
- site-event ingestion is append-only and non-blocking at the API layer
- Supabase remains the intended system of record, but runtime persistence is not wired yet

## Verification

- Python: `uv run pytest -q`
- Trigger.dev: `npx tsc -p trigger/tsconfig.json --noEmit`

## Source Of Truth

- `CONTEXT.md` for quick session routing
- `memory.md` for indexed master memory
- future runtime database for canonical business state

## Trigger Setup

- Set `TRIGGER_PROJECT_REF` in `.env` before running Trigger commands.
