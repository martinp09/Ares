# CODEX.md

## Purpose

This repo is the deterministic runtime and integration layer for a live Hermes agent deployment.

Hermes is the always-on control shell.
This repo owns typed commands, policy, orchestration wiring, provider adapters, and canonical-state integration.

## Communication

- Be terse. Lead with answer. No preamble.
- Do not restate the request unless needed to clarify risk.
- Ask only when blocked or when a decision changes architecture, data ownership, or live-system behavior.

## Core Architecture

- Hermes is the control fabric, not the source of truth.
- This repo is the reusable business runtime.
- Build a generalist core first, then add industry-specific capability packs.
- Real estate is the first optimization target, but avoid hard-coding the runtime to a single industry.
- Keep hard guarantees in code, services, jobs, and adapters, not in prompts.
- Provider-facing actions should go through deterministic adapters.

## Memory And Context

- Read `CONTEXT.md` first.
- Treat `CONTEXT.md` as the short router, TODO list, and quick-context file only.
- Keep `CONTEXT.md` under 50 lines, preferably 30.
- Use `memory.md` as the master indexed memory file.
- Read only the sections of `memory.md` referenced by `CONTEXT.md` unless the task clearly requires more.
- Update `CONTEXT.md` and `memory.md` after major work, especially after:
  - architecture changes
  - environment changes
  - migration work
  - provider integration changes
  - completed milestones

## WAT Model

Follow `WAT_Architecture.md`.

- Workflows define what to do.
- Agents coordinate decisions.
- Tools, services, and jobs perform deterministic execution.

## Subagent Orchestration

- For coding-heavy tasks, spawn `gpt-5.3-codex` subagents.
- For wiring tasks, use the least intelligent agent required, not the smallest or weakest overall, but the minimum required intelligence for the task.
- For planning or higher-level tasks, use `gpt-5.4` subagents.
- Choose reasoning effort based on task complexity.
- Spawn fresh subagents for each task. Do not reuse old ones.
- Close out subagents when finished.

## Resource Management

- When finished with servers or any process requiring memory, close it out.
- Do not leave servers, dev processes, browser sessions, MCP sessions, or background workers running when they are no longer needed.
- Kill stray processes right away once the task no longer requires them.
- Avoid accumulating temporary artifacts in tracked paths.

## Git And Delivery

- Prefer small, atomic commits over large commits.
- Keep repo bootstrap, infra changes, schema changes, and runtime features separated when practical.
- Match existing patterns and keep changes scoped.

## Runtime Direction

- Fresh Supabase project only. Do not inherit legacy database drift.
- Fresh migration chain in this repo.
- Trigger.dev is the durable orchestration layer.
- Marketing control plane comes before seller-ops cutover.
- Do not migrate seller-ops off `n8n` until the runtime backbone is proven.
