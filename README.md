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

## Source Of Truth

- `CONTEXT.md` for quick session routing
- `memory.md` for indexed master memory
- future runtime database for canonical business state
