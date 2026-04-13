# AGENTS.md

## Communication
- Be terse. Lead with answer. No preamble.
- No restating the request unless needed to clarify risk.
- Ask only when blocked or when a decision changes architecture or data ownership.

## Operating Model
- Read `CONTEXT.md` first.
- Treat `CONTEXT.md` as the router, TODO, and current scope file only.
- Keep `CONTEXT.md` under 50 lines, preferably under 30.
- Use `memory.md` as the master indexed memory file.
- Read only the `memory.md` sections referenced by `CONTEXT.md` unless the task clearly requires more.
- Update both `CONTEXT.md` and `memory.md` after meaningful work, especially after architecture decisions, environment changes, migrations, or execution milestones.

## Architecture
- Hermes is the control shell, not the business runtime.
- This repo is the deterministic runtime and integration layer Hermes controls.
- Keep workflows, agents, and tools separated per `WAT_Architecture.md`.
- Prefer additive, reusable industry packs over business-specific forks.

## Resource Management
- Close browser sessions, MCP sessions, and long-running processes when done.
- Avoid accumulating temp files and logs in tracked paths.

## Code Quality
- Minimal changes only.
- Match surrounding patterns.
- Keep hard guarantees in code, not in prompts.
- Provider actions should go through deterministic adapters.

## Memory
- `memory.md` is the master memory file.
- `CONTEXT.md` should point to specific `memory.md` sections, not duplicate them.
