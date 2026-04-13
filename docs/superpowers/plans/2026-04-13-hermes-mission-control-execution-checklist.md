# Hermes Mission Control AI-First Branch Execution Checklist

> Scope note: this checklist is for feature/mission-control-ai-first only.
> Environment note: Supabase wiring is deferred on this machine. We will scaffold the seams, contracts, and adapters here, then finish live Supabase wiring on Martin’s personal MacBook.
> Non-goals here: no page builder, no separate CRM, no duplicate scheduler, no duplicate queue engine, no live Supabase cutover.

**Goal:** Build the AI-first Mission Control branch from the docs in a phase-gated way, with concrete tests first and minimal code after, while keeping the current repo portable and scaffold-friendly.

**Architecture:** Hermes stays the control plane. FastAPI owns policy and typed runtime contracts. Trigger.dev owns durable execution. Supabase remains the intended canonical store, but this environment only scaffolds the persistence seam and keeps a working in-memory adapter. The Mission Control UI and agent primitives are added only after the runtime contract is stable.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, Trigger.dev, TypeScript, React/TypeScript later, Supabase later, pytest, uv, npm.

---

## Phase 1: Baseline lock and spec freeze

**Files:**
- Read: `README.md`
- Read: `CONTEXT.md`
- Read: `CODEX.md`
- Read: `WAT_Architecture.md`
- Read: `docs/superpowers/specs/2026-04-13-hermes-mission-control-architecture-design.md`
- Read: `docs/superpowers/specs/2026-04-13-hermes-mission-control-ui-design.md`
- Read: `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- Read: `docs/mission-control-wiki/index.md`
- Read: `docs/mission-control-wiki/concepts/agentic-first-command-center.md`
- Read: `docs/mission-control-wiki/concepts/managed-agent-runtime-patterns.md`
- Read: `docs/mission-control-wiki/entities/claude-managed-agents.md`
- Read: `docs/mission-control-wiki/comparisons/control-plane-vs-crm.md`
- Read: `docs/mission-control-wiki/comparisons/mcp-vs-a2a.md`

**Checks:**
- Confirm `apps/mission-control/` does not exist yet.
- Confirm the current runtime still uses in-memory control-plane state.
- Confirm the Trigger worker is still only the marketing scaffold.
- Confirm the docs agree on the same boundaries: Hermes = control plane, Trigger.dev = durable execution, Supabase = later canonical store, UI = native cockpit.

**Verification commands:**
- `uv run pytest -q`
- `npx tsc -p trigger/tsconfig.json --noEmit` if TypeScript dependencies are present

**Exit gate:** baseline understood, no code changes yet, no ambiguity about scope.

---

## Phase 2: Persistence seam scaffold only

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/core/config.py`
- Modify: `tests/test_package_layout.py`
- Create: `app/db/__init__.py`
- Create: `app/db/client.py`
- Create: `app/db/commands.py`
- Create: `app/db/approvals.py`
- Create: `app/db/runs.py`
- Create: `app/db/events.py`
- Create: `app/db/artifacts.py`
- Create: `tests/db/test_commands_repository.py`
- Create: `tests/db/test_approvals_repository.py`
- Create: `tests/db/test_runs_repository.py`

**First failing tests:**

`tests/db/test_commands_repository.py`
- create the same command twice returns the same command row via the repository abstraction
- a different `environment` does not collide with the same `idempotency_key`
- a different `command_type` does not collide with the same `idempotency_key`
- repository returns a normalized command shape with `deduped` support

`tests/db/test_approvals_repository.py`
- a newly inserted approval defaults to `pending`
- approving a row stores `actor_id` and `approved_at`
- fetching a missing approval returns `None`

`tests/db/test_runs_repository.py`
- creating a run stores `command_id`, `business_id`, `environment`, and `status`
- creating a replay child run stores `parent_run_id` and `replay_reason`
- appending two run events preserves order by `created_at`
- appending an artifact stores `artifact_type` and payload

`tests/test_package_layout.py`
- imports of `app.db.client`, `app.db.commands`, `app.db.approvals`, `app.db.runs`, `app.db.events`, and `app.db.artifacts` succeed
- package layout remains clean and importable from the repo root

**Minimal code after tests fail:**
- add a narrow `app/db/client.py` connection façade and transaction helper abstraction
- add repository interfaces or lightweight adapters that can run in-memory here
- do not wire a live Supabase client in this environment
- keep config fields minimal and scaffold-only; no production DB cutover yet
- keep the repository API compatible with the later live Supabase adapter

**Verification commands:**
- `uv run pytest tests/db/test_commands_repository.py tests/db/test_approvals_repository.py tests/db/test_runs_repository.py tests/test_package_layout.py -q`

**Exit gate:** the db seam exists, tests pass, and nothing depends on live Supabase.

---

## Phase 3: Runtime contract for commands, approvals, runs, and replays

**Files:**
- Modify: `app/models/commands.py`
- Modify: `app/models/approvals.py`
- Modify: `app/models/runs.py`
- Modify: `app/services/command_service.py`
- Modify: `app/services/approval_service.py`
- Modify: `app/services/run_service.py`
- Modify: `app/services/replay_service.py`
- Modify: `app/api/commands.py`
- Modify: `app/api/approvals.py`
- Modify: `app/api/runs.py`
- Modify: `app/api/replays.py`
- Modify: `tests/api/test_commands.py`
- Modify: `tests/api/test_approvals.py`
- Modify: `tests/api/test_runs.py`
- Modify: `tests/api/test_replays.py`

**First failing tests:**

`tests/api/test_commands.py`
- safe autonomous command returns `201`, `policy=safe_autonomous`, and a non-null `run_id`
- approval-required command returns `201`, `policy=approval_required`, and a non-null `approval_id`
- resubmitting the exact same command returns `200` with `deduped=true`

`tests/api/test_approvals.py`
- approving a pending approval returns a run ID
- approving the same approval twice returns the same run ID
- approving a missing approval returns `404`

`tests/api/test_runs.py`
- `GET /runs/{run_id}` returns a persisted run with `events` and `artifacts`
- a replay-created child run exposes `parent_run_id`

`tests/api/test_replays.py`
- replaying a safe autonomous run returns `201` with `requires_approval=false`
- replaying an approval-required run returns `409` with `requires_approval=true`
- replay responses include `replay_reason`

**Minimal code after tests fail:**
- keep policy classification in `app/services/command_service.py`
- move state access through the repository seam created in Phase 2
- preserve the in-memory adapter for this environment
- keep endpoint ownership unchanged:
  - commands = typed ingestion boundary
  - approvals = approval boundary
  - runs = read boundary
  - replays = replay boundary
- do not move policy into Trigger.dev

**Verification commands:**
- `uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py -q`

**Exit gate:** the runtime contract is deterministic, repository-backed through the seam, and still works with the in-memory adapter.

---

## Phase 4: Trigger callback contract and lifecycle wiring

**Files:**
- Modify: `trigger/trigger.config.ts`
- Modify: `trigger/bootstrap.ts`
- Modify: `trigger/src/shared/runtimeApi.ts`
- Modify: `trigger/src/marketing/runMarketResearch.ts`
- Modify: `trigger/src/marketing/createCampaignBrief.ts`
- Modify: `trigger/src/marketing/draftCampaignAssets.ts`
- Modify: `trigger/src/marketing/assembleLaunchProposal.ts`
- Modify: `app/main.py`
- Modify: `tests/api/test_marketing_runtime.py`
- Modify: `tests/domains/marketing/test_marketing_flow.py`
- Create: `trigger/src/runtime/dispatchCommand.ts`
- Create: `trigger/src/runtime/reportRunLifecycle.ts`
- Create: `trigger/src/runtime/queueKeys.ts`
- Create: `app/models/run_events.py`
- Create: `app/api/trigger_callbacks.py`
- Create: `app/services/run_lifecycle_service.py`
- Create: `tests/api/test_trigger_callbacks.py`

**First failing tests:**

`tests/api/test_trigger_callbacks.py`
- posting `run_started` updates a run from `queued` to `in_progress`
- posting `artifact_produced` appends an artifact row without mutating prior artifacts
- posting `run_completed` sets the run status to `completed`
- posting `run_failed` sets the run status to `failed` and stores the error payload

`tests/api/test_marketing_runtime.py`
- the marketing endpoints still return the expected artifact types
- the runtime callback payloads match the TypeScript worker contract exactly

`tests/domains/marketing/test_marketing_flow.py`
- the marketing command still maps to the same ordered task chain
- the Trigger-side dispatch helper does not duplicate steps

**Minimal code after tests fail:**
- add the Hermes-owned callback boundary for Trigger.dev
- translate callback payloads into runtime-owned lifecycle events
- keep Trigger.dev as the durable executor only
- use Trigger queues and retries directly; do not add a Hermes scheduler, retry engine, or canvas
- keep queue keys tenant-aware (`businessId`, `environment`)
- ensure each marketing task reports `run_started`, artifact creation, and exactly one terminal status event

**Verification commands:**
- `npx tsc -p trigger/tsconfig.json --noEmit`
- `uv run pytest tests/api/test_trigger_callbacks.py tests/api/test_marketing_runtime.py tests/domains/marketing/test_marketing_flow.py -q`

**Exit gate:** Trigger.dev is the execution layer, Hermes is still the canonical state layer, and lifecycle callbacks are explicit.

---

## Phase 5: Managed-agent primitives and connect-later operational assets

**Files:**
- Modify: `app/services/hermes_tools_service.py`
- Modify: `app/api/hermes_tools.py`
- Modify: `app/main.py`
- Modify: `tests/api/test_hermes_tools.py`
- Modify: `tests/test_package_layout.py`
- Create: `supabase/migrations/202604130003_mission_control_managed_agents.sql`
- Create: `app/db/agents.py`
- Create: `app/db/sessions.py`
- Create: `app/db/permissions.py`
- Create: `app/db/outcomes.py`
- Create: `app/models/agents.py`
- Create: `app/models/sessions.py`
- Create: `app/models/permissions.py`
- Create: `app/models/outcomes.py`
- Create: `app/models/agent_assets.py`
- Create: `app/services/agent_registry_service.py`
- Create: `app/services/session_service.py`
- Create: `app/services/permission_service.py`
- Create: `app/services/outcome_service.py`
- Create: `app/services/agent_asset_service.py`
- Create: `app/api/agents.py`
- Create: `app/api/sessions.py`
- Create: `app/api/outcomes.py`
- Create: `app/api/agent_assets.py`
- Create: `tests/api/test_agents.py`
- Create: `tests/api/test_sessions.py`
- Create: `tests/api/test_outcomes.py`
- Create: `tests/api/test_agent_assets.py`

**First failing tests:**

`tests/api/test_agents.py`
- creating an agent creates a stable `agent_id` and an initial `draft` revision
- publishing a draft revision marks it as the active production revision
- cloning a published revision creates a new draft revision with copied config
- archived revisions remain queryable but cannot be published again

`tests/api/test_sessions.py`
- creating two sessions from the same revision produces isolated session IDs and thread timelines
- a session cannot be created from an archived revision
- a session still points to the original revision after a newer revision is published

`tests/api/test_outcomes.py`
- evaluating an outcome stores rubric criteria and evaluator result
- a failed rubric stores failure details without mutating the original artifact
- a passed rubric marks the outcome as satisfied

`tests/api/test_agent_assets.py`
- creating an unbound asset stores `connect_later=true`
- binding a connect-later asset updates only the asset record, not the agent revision
- asset types outside operational scope are rejected

`tests/api/test_hermes_tools.py`
- a tool with `always_ask` permission returns an approval path instead of direct execution
- a tool with `forbidden` permission is rejected

**Minimal code after tests fail:**
- implement versioned agent definitions with immutable revisions
- keep sessions isolated from agent definition mutation
- add explicit permissions: `always_allow`, `always_ask`, `forbidden`
- add outcome/rubric evaluation as a Hermes-native control-plane primitive
- add connect-later operational assets only for operational bindings like calendars, forms, phone numbers, inboxes, and webhook-backed assets
- exclude landing pages and page-builder artifacts completely
- register new routers in `app/main.py`
- expose agent-aware tools without bypassing permission checks

**Verification commands:**
- `uv run pytest tests/api/test_agents.py tests/api/test_sessions.py tests/api/test_outcomes.py tests/api/test_agent_assets.py tests/api/test_hermes_tools.py tests/test_package_layout.py -q`

**Exit gate:** versioned agents, isolated sessions, permissions, outcomes, and operational assets all work without turning into a page builder or a duplicate orchestration system.

---

## Phase 6: Mission Control read models and native UI shell

**Files:**
- Modify: `package.json`
- Modify: `app/main.py`
- Create: `app/models/mission_control.py`
- Create: `app/services/mission_control_service.py`
- Create: `app/api/mission_control.py`
- Create: `tests/api/test_mission_control.py`
- Create: `apps/mission-control/package.json`
- Create: `apps/mission-control/tsconfig.json`
- Create: `apps/mission-control/index.html`
- Create: `apps/mission-control/vite.config.ts`
- Create: `apps/mission-control/vitest.config.ts`
- Create: `apps/mission-control/src/main.tsx`
- Create: `apps/mission-control/src/App.tsx`
- Create: `apps/mission-control/src/styles.css`
- Create: `apps/mission-control/src/lib/api.ts`
- Create: `apps/mission-control/src/lib/queryClient.ts`
- Create: `apps/mission-control/src/pages/DashboardPage.tsx`
- Create: `apps/mission-control/src/pages/InboxPage.tsx`
- Create: `apps/mission-control/src/pages/ApprovalsPage.tsx`
- Create: `apps/mission-control/src/pages/RunsPage.tsx`
- Create: `apps/mission-control/src/pages/AgentsPage.tsx`
- Create: `apps/mission-control/src/pages/SettingsPage.tsx`
- Create: `apps/mission-control/src/components/MissionControlShell.tsx`
- Create: `apps/mission-control/src/components/DashboardSummary.tsx`
- Create: `apps/mission-control/src/components/InboxList.tsx`
- Create: `apps/mission-control/src/components/ConversationThread.tsx`
- Create: `apps/mission-control/src/components/ContextPanel.tsx`
- Create: `apps/mission-control/src/components/ApprovalQueue.tsx`
- Create: `apps/mission-control/src/components/RunTimeline.tsx`
- Create: `apps/mission-control/src/components/AgentRegistryTable.tsx`
- Create: `apps/mission-control/src/components/ConnectLaterPanel.tsx`
- Create: `apps/mission-control/src/test/setup.ts`
- Create: `apps/mission-control/src/components/MissionControlShell.test.tsx`
- Create: `apps/mission-control/src/pages/DashboardPage.test.tsx`

**First failing tests:**

`tests/api/test_mission_control.py`
- dashboard endpoint returns approval count, active run count, failed run count, and active agent count
- inbox endpoint returns conversation summaries plus a selected thread payload
- runs endpoint returns run lineage including `parent_run_id`
- agents endpoint returns revision state and active production revision
- settings/assets endpoint returns connect-later asset status

`apps/mission-control/src/components/MissionControlShell.test.tsx`
- shell renders the left navigation and active workspace

`apps/mission-control/src/pages/DashboardPage.test.tsx`
- dashboard renders counts from the backend response without embedding business logic in the component

**Minimal code after tests fail:**
- build backend read models first
- expose stable Mission Control read routes from Hermes
- keep the UI native to this repo, dense, and operational
- keep all writes flowing back through Hermes APIs
- include only the cockpit surfaces from the spec: dashboard, inbox, approvals, runs, agents, settings/assets
- do not add page-builder, landing-page, or funnel-editor screens

**Verification commands:**
- `npm --prefix apps/mission-control install`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`
- `uv run pytest tests/api/test_mission_control.py -q`

**Exit gate:** the UI is native, backend-driven, and centered on inbox, approvals, runs, agents, and operational asset binding.

---

## Phase 7: Final documentation sync and release gate

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `docs/superpowers/specs/2026-04-13-hermes-mission-control-architecture-design.md`
- Modify: `docs/superpowers/specs/2026-04-13-hermes-mission-control-ui-design.md`
- Modify: `docs/mission-control-wiki/index.md`
- Modify: `docs/mission-control-wiki/concepts/agentic-first-command-center.md`
- Modify: `docs/mission-control-wiki/concepts/managed-agent-runtime-patterns.md`
- Modify: `docs/mission-control-wiki/concepts/mission-control-ui.md`
- Modify: `docs/mission-control-wiki/entities/claude-managed-agents.md`
- Modify: `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`

**Checklist:**
- update docs so they match the shipped architecture
- keep the same boundaries everywhere:
  - Hermes = control plane
  - Supabase/Postgres = canonical state layer
  - Trigger.dev = durable execution layer
  - Claude Managed Agents = versioning, sessions, permissions, events, outcomes
  - GoHighLevel patterns = draft/production, clone ergonomics, connect-later operational assets
  - page builders and landing pages = out of scope
- update `CONTEXT.md` and `memory.md` with the completion status and latest change-log entry
- fix any docs that still point at stale paths or stale architecture assumptions

**Verification commands:**
- `supabase db reset --local` only if a local database is actually available in the environment
- `uv run pytest -q`
- `npx tsc -p trigger/tsconfig.json --noEmit`
- `npm --prefix apps/mission-control run build`
- `git diff --check`

**Exit gate:** every phase is reflected in the docs, the docs match the code, and there are no contradictions left behind.

---

## Execution rules

- Do not skip phase gates.
- Keep Supabase wiring deferred here; only scaffold the seam.
- Keep policy in FastAPI, not in Trigger.dev or the frontend.
- Keep the repo portable and installable anywhere.
- Keep feature additions aligned with the AI-first control-plane vision.
- If a step would introduce duplicate orchestration infrastructure, stop and re-scope it.
