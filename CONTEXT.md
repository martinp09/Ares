# Context

> Read this file first. Use it as the router only. Do not load all of `memory.md` by default.

## Stable Facts

- Repo: Ares (local path `/home/workspace/Hermes-Central-Command/.worktrees/loose-ends`)
- Purpose: reusable Hermes-controlled business runtime
- Operating model: generalist core first, industry packs second
- First optimization target: real estate
- Source of truth:
  - `CONTEXT.md` = scope, TODOs, router
  - `memory.md` = master indexed memory

## Current Scope

1. keep the branch clean and defer live Supabase wiring for this job
2. finish every safe in-memory/runtime/document/UI slice that does not require Supabase
3. keep the runtime/app split explicit: Hermes shell here, seller-ops legacy stays outside
4. implement the lead-machine / marketing control plane in-memory first
5. keep managed-agent primitives scaffolded in-memory until live Supabase wiring happens on Martin's MacBook
6. keep Mission Control read models and the native frontend shell scaffold-first; the Intake happy-path view stays fixture-backed
7. keep the Mission Control UI aligned to the approved dark industrial terminal / pixel CRT style system
8. use think-before-coding for code edits and agentic-workflow-best-practices for multi-step orchestration work
9. use claude-code-memory-best-practices, claude-code-settings-best-practices, claude-code-mcp-best-practices, claude-code-startup-flags-best-practices, and claude-code-power-ups-best-practices when working on Claude Code ergonomics or session configuration
10. Phase 1 org tenancy plumbing for turn-loop routes is now wired in-memory; the phase-2 API cleanup (unknown-skill 422 translation + scoped session fixtures) is passing in this worktree
11. The current branch scope is the probate outbound + lease-option inbound MVP, not the enterprise-platform backlog
12. story-02 probate write path acceptance is verified in-memory (`/lead-machine/probate/intake`, `/lead-machine/outbound/enqueue`, `/lead-machine/webhooks/instantly`)
13. story-03 lease-option inbound hardening is verified in-memory (sequence guard state, booking confirmation timeline logging, thread-first SMS resolution, ambiguity tasking)
14. inbound SMS QC blockers are fixed in-memory: duplicate-thread resolution now stays tenant-scoped and shared-phone stop/pause mutations stay bound to the resolved lead
15. story-04 mission-control dual-lane surfaces are verified in-memory (lane-specific dashboard summaries + lane-separated pipeline stage summaries in API and UI)
16. story-05 thin opportunity seam is verified in-memory (forward stage updates covered + lease-option operator-ready path advances opportunity stage)
17. story-06 rollout gates are verified in-memory (backend + Mission Control + Trigger checks passing, both lane fixture smokes passing, memory-mode startup confirmed with Supabase env vars unset)

## Current TODO

1. keep `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md` as the completed MVP execution reference
2. keep `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md` and `docs/superpowers/plans/2026-04-17-ares-scaffold-completion-plan.md` as the live branch inputs
3. keep the two live lanes stable on Supabase:
   - probate outbound via Instantly
   - lease-option inbound via marketing submit / booking / SMS
4. keep Mission Control additive:
   - `Lead Machine`
   - `Marketing`
   - `Pipeline`
5. keep the shared control-plane Supabase lift complete and smokeable:
   - done: `commands`, `approvals`, `runs`, `events`, `artifacts`
   - done: managed-agent/session/turn/RBAC/audit/runtime tables now use the shared Supabase-backed transaction path
   - next: remote smoke and any schema cleanup it exposes
6. use `scripts/ralph/prd.json`, `scripts/ralph/session-prompt.md`, and `scripts/ralph/watchdog.sh` for fresh-session Ralph/Codex loops on this branch
7. keep `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md` archived, not live scope

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Current Runtime Surface`
2. `## Repo Conventions`
3. `## Environment Notes`
4. `## Open Work`
5. latest entry in `## Change Log`
