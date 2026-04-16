# Ares Turn Engine Robustness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Ares into a robust, event-driven agent runtime that borrows Claw Code’s best loop, retry, permission, and compaction patterns while staying portable, Python/FastAPI-native, and Mission-Control-visible.

**Architecture:** Ares keeps the current host-agnostic core and adds a deterministic turn engine around it. The turn engine owns message assembly, provider calls, tool execution, retries, permission checks, compaction, and session journaling. Mission Control becomes the operator surface for observing and approving those turns, not the source of truth.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, in-memory repositories for the current slice, TypeScript/Vite Mission Control UI, pytest/Vitest.

---

## What to steal from Claw Code

| Claw Code pattern | Ares implementation | Ares improvement |
|---|---|---|
| Single turn loop in `conversation.rs` | `TurnRunnerService` in Python | Event-first turn journal, cancellation, resumable turns |
| Provider abstraction in API clients | Provider adapters behind one Python interface | Explicit config-driven routing, capability metadata |
| Jittered retry/backoff | Central retry policy service | Retry-After support, circuit breakers, structured error states |
| Permission policy + enforcer | Capability-based permission service | Stronger sandbox/path boundaries, audit trail, approval UX |
| Compaction that preserves tool/result pairs | Structured compaction + session journal | JSON memory source of truth, async compaction |
| CLI/runtime glue | Backend services + Mission Control API | No CLI lock-in; backend-first product shape |

---

## Concrete Ares module/file map

### Existing files that become the center of gravity
- `app/services/agent_registry_service.py`
- `app/services/session_service.py`
- `app/services/permission_service.py`
- `app/services/mission_control_service.py`
- `app/services/run_service.py`
- `app/api/agents.py`
- `app/api/sessions.py`
- `app/api/permissions.py`
- `app/api/runs.py`
- `app/api/mission_control.py`
- `app/core/config.py`
- `apps/mission-control/src/pages/InboxPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`
- `apps/mission-control/src/pages/AgentsPage.tsx`
- `apps/mission-control/src/components/ConversationThread.tsx`
- `apps/mission-control/src/components/RunTimeline.tsx`

### New backend modules to create
- `app/models/turns.py`
  - typed turn events, provider responses, tool call envelopes, retry metadata
- `app/services/turn_runner_service.py`
  - the core turn/query engine
- `app/services/provider_registry_service.py`
  - selects and instantiates provider adapters explicitly
- `app/services/provider_retry_service.py`
  - shared transient-error retry policy and backoff helper
- `app/services/provider_preflight_service.py`
  - token/context/tool-schema validation before network calls
- `app/services/compaction_service.py`
  - structured compaction and continuation prompt generation
- `app/services/tool_hook_service.py`
  - pre-tool and post-tool hooks with structured outcomes
- `app/db/turn_events.py`
  - append-only turn journal for session replay/resume
- `app/models/providers.py`
  - provider request/response schemas and capability metadata
- `app/models/capabilities.py`
  - capability profiles for tools, skills, host adapters, and sessions
- `app/models/session_journal.py`
  - session snapshot + turn journal projection models
- `app/services/providers/`
  - `base.py`, `anthropic.py`, `openai_compat.py`, `local.py` if needed later

### Backend files to modify
- `app/services/session_service.py`
  - attach sessions to the turn journal and compaction metadata
- `app/services/permission_service.py`
  - resolve capability policy and human approval modes
- `app/services/agent_registry_service.py`
  - store provider policy and capability requirements on revisions
- `app/services/mission_control_service.py`
  - expose turn state, retry state, approvals, and compaction status
- `app/api/sessions.py`
  - add turn-start / turn-resume / turn-events endpoints if needed
- `app/api/mission_control.py`
  - add operator endpoints for turn inspection and approval flows
- `app/api/agents.py`
  - persist provider/capability metadata on agent revisions
- `app/core/config.py`
  - add provider auth, retry, token-budget, and compaction settings

### Frontend files to modify
- `apps/mission-control/src/pages/InboxPage.tsx`
  - show live turn state for the selected thread/session
- `apps/mission-control/src/pages/RunsPage.tsx`
  - show turn retries, tool calls, and compaction checkpoints
- `apps/mission-control/src/pages/AgentsPage.tsx`
  - show revision capabilities, provider choice, and host adapter visibility
- `apps/mission-control/src/components/ConversationThread.tsx`
  - render turn event stream, approvals, tool calls, retries, and failures
- `apps/mission-control/src/components/RunTimeline.tsx`
  - include retry markers, tool boundaries, and compaction markers
- `apps/mission-control/src/lib/fixtures.ts`
  - extend fixtures for turn events, retries, and approval states

### Tests to add or update
- `tests/services/test_turn_runner_service.py`
- `tests/services/test_provider_retry_service.py`
- `tests/services/test_provider_preflight_service.py`
- `tests/services/test_compaction_service.py`
- `tests/services/test_tool_hook_service.py`
- `tests/services/test_permission_service.py`
- `tests/api/test_turns.py`
- `tests/api/test_mission_control.py`
- `tests/api/test_sessions.py`
- `tests/db/test_turn_events_repository.py`
- `apps/mission-control/src/pages/InboxPage.test.tsx`
- `apps/mission-control/src/pages/RunsPage.test.tsx`
- `apps/mission-control/src/components/ConversationThread.test.tsx`

---

## Build order

### Task 1: Turn runner core
**Files:**
- Create: `app/models/turns.py`
- Create: `app/services/turn_runner_service.py`
- Create: `app/db/turn_events.py`
- Modify: `app/services/session_service.py`
- Modify: `app/api/sessions.py`
- Test: `tests/services/test_turn_runner_service.py`
- Test: `tests/api/test_sessions.py`
- Test: `tests/db/test_turn_events_repository.py`

**What this delivers:**
- one deterministic turn loop
- turn lifecycle events
- persisted session journal
- resumable state after retries or crashes

**Acceptance gate:**
- turn completes with no tool calls
- tool-call turn re-enters correctly
- event journal survives replay

### Task 2: Provider adapters + auth registry
**Files:**
- Create: `app/models/providers.py`
- Create: `app/services/provider_registry_service.py`
- Create: `app/services/providers/base.py`
- Create: `app/services/providers/anthropic.py`
- Create: `app/services/providers/openai_compat.py`
- Create: `app/services/providers/local.py`
- Modify: `app/core/config.py`
- Test: `tests/services/test_provider_registry_service.py`
- Test: `tests/services/test_provider_clients.py`

**What this delivers:**
- one provider contract for streaming and non-streaming calls
- explicit provider selection per agent/workspace
- normalized request/response shape

**Acceptance gate:**
- Anthropic and OpenAI-compatible providers can both stream through the same interface
- provider capability metadata is visible to the turn runner

### Task 3: Retry and preflight policy
**Files:**
- Create: `app/services/provider_retry_service.py`
- Create: `app/services/provider_preflight_service.py`
- Modify: `app/services/providers/anthropic.py`
- Modify: `app/services/providers/openai_compat.py`
- Test: `tests/services/test_provider_retry_service.py`
- Test: `tests/services/test_provider_preflight_service.py`

**What this delivers:**
- one retry policy for transient upstream failures
- token/context/tool-size checks before network calls
- structured retry state for Mission Control

**Acceptance gate:**
- 429/408/5xx and timeout cases retry with backoff
- Retry-After is honored when present
- oversized requests fail before the upstream call

### Task 4: Capability permissions and tool hooks
**Files:**
- Create: `app/models/capabilities.py`
- Create: `app/services/tool_hook_service.py`
- Modify: `app/services/permission_service.py`
- Modify: `app/services/turn_runner_service.py`
- Modify: `app/services/agent_registry_service.py`
- Test: `tests/services/test_permission_service.py`
- Test: `tests/services/test_tool_hook_service.py`

**What this delivers:**
- capability-based allow/ask/deny model
- pre-tool and post-tool hook seam
- human approval path for risky actions

**Acceptance gate:**
- tool execution is denied without the right capability
- hook overrides are structured, not free-form side effects
- approval decisions are auditable

### Task 5: Structured compaction and memory
**Files:**
- Create: `app/services/compaction_service.py`
- Create: `app/models/session_journal.py`
- Modify: `app/services/session_service.py`
- Modify: `app/services/turn_runner_service.py`
- Modify: `app/services/mission_control_service.py`
- Test: `tests/services/test_compaction_service.py`

**What this delivers:**
- compaction that preserves tool/result pairs
- structured memory summaries
- resumable session continuation prompts

**Acceptance gate:**
- no broken tool call/result boundaries
- summary preserves goals, completed work, pending work, and blockers

### Task 6: Mission Control visibility
**Files:**
- Modify: `app/api/mission_control.py`
- Modify: `apps/mission-control/src/pages/InboxPage.tsx`
- Modify: `apps/mission-control/src/pages/RunsPage.tsx`
- Modify: `apps/mission-control/src/pages/AgentsPage.tsx`
- Modify: `apps/mission-control/src/components/ConversationThread.tsx`
- Modify: `apps/mission-control/src/components/RunTimeline.tsx`
- Modify: `apps/mission-control/src/lib/fixtures.ts`
- Test: `apps/mission-control/src/pages/InboxPage.test.tsx`
- Test: `apps/mission-control/src/pages/RunsPage.test.tsx`
- Test: `apps/mission-control/src/components/ConversationThread.test.tsx`

**What this delivers:**
- operators can see retries, approvals, tool calls, and compaction points
- event stream is visible in the UI
- no hidden agent loop state

**Acceptance gate:**
- the UI tells the truth about turn state
- fixture-backed screens still render without live wiring

---

## Do-not-copy list
- Do not copy Claw Code’s CLI-first product shape into Ares.
- Do not use env-sniffed provider routing as the main control path.
- Do not rely on string-prefix path checks as the real security boundary.
- Do not treat plain-text summaries as canonical memory.
- Do not add a second source of truth when one canonical service can own it.

## Ares-specific improvements over Claw Code
- Event-first turn journal instead of only message-based state.
- Explicit provider selection instead of mostly implicit environment detection.
- Capability model that matches Ares host adapters and skills.
- Structured compaction memory instead of summary-only compaction.
- Mission Control as a real operator console for retries, approvals, and turn tracing.

## Verification
Run after each task and again at the end:
- `uv run pytest -q`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`
- `git diff --check`

## Final build order recommendation
1. Turn runner + event journal
2. Provider registry + auth wrappers
3. Retry/preflight policy
4. Capability permissions + hooks
5. Structured compaction/memory
6. Mission Control event visibility
7. Contract tests across the whole loop

## Exit gate
Do not call the runtime robust until a single turn can:
- authenticate
- preflight
- stream
- call tools
- retry transient provider failures
- compact safely
- surface the whole chain in Mission Control
