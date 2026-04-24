# Ares Supabase Wiring Map From Memory

> Status: planning / wiring map only.
>
> Created: 2026-04-24.
>
> Repo inspected: `/home/workspace/Hermes-Central-Command` on `feature/ares-enterprise-platform`.
>
> Purpose: consolidate remembered context, repo memory, prior-session summaries, and current code evidence into one document that says what still needs Supabase wiring.

## Executive Summary

Ares currently has three different persistence states:

1. **Runtime/control plane is still in-memory.**
   - `app/db/client.py` exposes `SupabaseControlPlaneClient`, but its `transaction()` method raises `NotImplementedError`.
   - `control_plane_backend` defaults to `memory`.
   - Current in-memory store includes commands, approvals, runs, agents, revisions, sessions, permissions, outcomes, skills, host adapter dispatches, assets, and Mission Control threads.

2. **Marketing has a partial Supabase REST adapter.**
   - `app/db/marketing_supabase.py` exists.
   - Contacts, conversations, messages, bookings, tasks, and sequence enrollments have Supabase paths behind `marketing_backend=supabase`.
   - Repo memory says a marketing-only Supabase adapter was live-smoked against remote `public.contacts` for `limitless/dev`, and core + lease-option migrations were applied to project `awmsrjeawcxndfnggoxw`.

3. **Site events default to Supabase but are isolated from the main control-plane adapter.**
   - `site_events_backend` defaults to `supabase`.
   - `app/domains/site_events/service.py` writes directly to Supabase REST using `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

The missing work is **not one big “turn on Supabase” switch**. It is a staged cutover: schema reconciliation, repository adapters, service migration, Mission Control read-model migration, enterprise-platform table migrations, then preview/staging/production gates. Do not do the clown move where we flip `control_plane_backend=supabase` while the adapter still throws.

## Memory Sources Used

### Durable / repo memory

- `CONTEXT.md`
  - Current scope says: defer live Supabase wiring for this job.
  - Managed-agent primitives stay scaffolded in memory until live Supabase wiring happens on Martin's MacBook.
  - Mission Control read models and frontend shell stay scaffold-first.
  - Next follow-on plan: durable checkpoints, persistent memory, stream visibility, sandboxed execution, integration surfaces, and scheduled work.

- `memory.md`
  - Supabase is intended as canonical state and audit.
  - Current storage mode is in-memory for commands, approvals, runs, site events, agents, revisions, sessions, permissions, outcomes, and operational assets.
  - Mission Control remains fixture-backed until live backend wiring is intentionally enabled later.
  - Fresh Supabase project was created for Ares.
  - Local `.env` should be ported from the validated `Mailers AWF` environment as needed.
  - Marketing-only Supabase adapter was added and smoke-tested into remote `public.contacts` for `limitless/dev`.
  - Core and lease-option marketing migrations were applied to Supabase project `awmsrjeawcxndfnggoxw` and `public.businesses` was seeded with `limitless/dev`.
  - Remaining MVP risks: inbound SMS matching is still phone-only; sequence guard state is too simplistic for multi-tenant or advanced sequence rollout.

### Mem0 / recalled memory

- Supabase/database wiring stays on Martin's MacBook.
- User previously required reconstructing Ares state from git/docs, not trusting chat-only context.
- User's hard rules from prior takeover prompt:
  - never touch Supabase from the wrong environment,
  - preserve non-Supabase wiring,
  - avoid destructive migrations,
  - keep `business_id + environment` alive,
  - require green tests before claiming completion.
- User wants the remaining work documented phase-by-phase and task-by-task.
- User wants correct long-term code, not quick temporary fixes.

### Prior session summaries

- The old `feature/mission-control-supabase-persistence` branch had a dedicated design-only persistence rollout plan.
- That plan said persistence must be isolated from Mission Control contract fixes and should proceed through local reset, preview/staging, then production.
- The remembered current in-memory surfaces to replace were:
  - commands,
  - approvals,
  - runs,
  - run events,
  - artifacts,
  - agents,
  - agent revisions,
  - sessions,
  - permissions,
  - outcomes,
  - agent assets,
  - Mission Control threads.
- Previous Phase 7 / enterprise backlog memory says Supabase wiring remained deferred while non-Supabase runtime/UI/enterprise slices were completed or reviewed.

## Current Code Evidence

### Config switches

File: `app/core/config.py`

```text
control_plane_backend: memory | supabase = memory
marketing_backend: memory | supabase = memory
site_events_backend: memory | supabase = supabase
supabase_url
supabase_service_role_key
database_url
```

Implications:

- `control_plane_backend=supabase` is currently unsafe because the control-plane adapter is not implemented.
- `marketing_backend=supabase` has partial implementation and can be tested independently.
- `site_events_backend=supabase` already uses direct REST persistence, so local/dev without Supabase creds can fail if site events are exercised unless explicitly set to `memory`.

### Control-plane adapter is not implemented

File: `app/db/client.py`

Current in-memory store fields:

- `commands`
- `command_keys`
- `approvals`
- `runs`
- `agents`
- `agent_revisions`
- `agent_revision_ids_by_agent`
- `sessions`
- `session_memory_summaries`
- `turns`
- `turn_events`
- `turn_ids_by_session`
- `permissions`
- `permission_keys`
- `outcomes`
- `skills`
- `skill_keys`
- `host_adapter_dispatches`
- `agent_assets`
- `mission_control_threads`

`SupabaseControlPlaneClient.transaction()` currently raises:

```text
Live Supabase wiring is deferred in this environment; use the in-memory control-plane adapter for now.
```

This is the master list of durable state still needing Supabase-backed repositories or an equivalent adapter contract.

### Existing migrations

Current branch contains:

- `supabase/migrations/202604130001_hermes_control_plane_core.sql`
  - includes `businesses`, `commands`, `approvals`, `runs`, `tasks`, `artifacts`, `events`, `contacts`, `conversations`, `site_events`.
  - includes tenant columns `business_id` + `environment`.
  - includes command idempotency unique index.
  - includes append-only guards for `events` and `site_events`.
  - includes RLS policies keyed by `business_id` + `environment`.

- `supabase/migrations/202604130003_mission_control_managed_agents.sql`
  - placeholder only.
  - explicitly says live Supabase wiring is deferred.
  - intended future tables:
    - `agents`
    - `agent_revisions`
    - `agent_sessions`
    - `agent_tool_permissions`
    - `outcome_evaluations`
    - `agent_operational_assets`

- `supabase/migrations/202604140001_lease_option_marketing_mvp.sql`
  - includes `messages`, `booking_events`, `sequence_enrollments`.
  - includes tenant FKs and RLS.
  - includes active sequence uniqueness.

The old remote branch `origin/feature/mission-control-supabase-persistence` also contained these additional persistence migrations that are **not** present in the current branch:

- `202604130002_mission_control_runtime_persistence.sql`
- `202604130004_managed_agent_persistence_tables.sql`
- `202604130005_managed_agents_sessions_persistence.sql`

Those old branch artifacts should be treated as reference material, not blindly copied. Current branch reality wins.

## Supabase Wiring Still Needed

## 0. Preflight / Safety Gate

### 0.1 Confirm target project and credentials

Needed:

- Confirm the intended Supabase project ref.
- Confirm whether the target remains `awmsrjeawcxndfnggoxw` or a new staging/preview project.
- Confirm `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and DB password / pooler URL.
- Confirm whether local Supabase is available on Martin's MacBook.

Source evidence:

- `memory.md` says project `awmsrjeawcxndfnggoxw` had core + lease-option migrations applied.
- Mem0 says Supabase/database wiring stays on Martin's MacBook.
- Supabase recovery skill says verify project ref, `.env`, `supabase/.temp/project-ref`, and pooler URL before pushing anything.

Acceptance:

- A written target-project line exists before any migration.
- `supabase db push --dry-run` or local reset target is known.
- No migration is applied from this hosted environment unless explicitly authorized.

### 0.2 Freeze migration rules

Needed:

- Do not rewrite `202604130001_hermes_control_plane_core.sql`.
- Treat `202604130003_mission_control_managed_agents.sql` as historical scaffold unless intentionally superseded with additive migrations.
- Add new migrations only.
- Keep `business_id + environment` on all existing runtime contracts.
- Add `org_id` additively where enterprise scope requires it.

Source evidence:

- Enterprise plan cross-phase migration rules.
- Mission Control finish plan Chunk 2.
- Mem0 hard-rule memory: preserve non-Supabase wiring, avoid destructive migrations, keep `business_id + environment` alive.

Acceptance:

- New migration names are monotonic and additive.
- `git diff` never edits the already-applied baseline unless the user explicitly approves a rebuild, which is not the current path.

## 1. Runtime Core Persistence

This is the first real control-plane cutover. Do it before managed-agent persistence.

### 1.1 Reconcile Python IDs/statuses with SQL schema

Needed decisions:

- Current Python IDs use string prefixes like `cmd_*`, `apr_*`, `run_*`; baseline SQL uses bigint identity primary keys.
- Decide whether to:
  - add text runtime IDs as unique public/business keys while bigint stays internal, or
  - migrate SQL primary keys to text in additive successor tables/views, or
  - build explicit mapping at repository boundary.
- Resolve enum drift:
  - Python `CommandStatus` includes `accepted` / `awaiting_approval`; SQL uses `queued` / `approval_required`.
  - Python run status may use `in_progress`; SQL uses `running`.
  - Python approvals expose `approved_at`; SQL baseline has `decided_at`.

Source evidence:

- Remote persistence plan schema-risk notes.
- Current tests/API expect current payload shapes.
- Current SQL baseline uses bigint identities.

Acceptance:

- Repository tests prove API payload shape does not change under Supabase.
- Mappers live in repository/adapter layer, not scattered service-by-service like glitter in carpet.

### 1.2 Implement command repository adapter

Needed:

- Supabase-backed command create/dedupe/read/list.
- Preserve unique idempotency on `(business_id, environment, command_type, idempotency_key)`.
- Preserve policy classification result and status transitions.
- Preserve API behavior:
  - first create returns `201`,
  - duplicate idempotency returns `200` with `deduped=true`.

Files likely involved:

- `app/db/commands.py`
- `app/services/command_service.py`
- `tests/db/test_commands_repository.py`
- `tests/api/test_commands.py`

Acceptance:

- Memory and Supabase adapters both pass command API tests.

### 1.3 Implement approval repository adapter

Needed:

- Supabase-backed pending approval creation/list/get/approve/reject.
- Preserve approval-required command behavior.
- Preserve idempotent approval behavior: re-approving must not create duplicate runs.
- Store actor/decision metadata consistently.

Files likely involved:

- `app/db/approvals.py`
- `app/services/approval_service.py`
- `tests/db/test_approvals_repository.py`
- `tests/api/test_approvals.py`

Acceptance:

- Approval queue in Mission Control reads from durable approval facts.
- Approving a pending item creates exactly one run.

### 1.4 Implement runs/events/artifacts repository adapters

Needed:

- Supabase-backed run create/get/list/update lifecycle.
- Normalize run events into `public.events`.
- Normalize run artifacts into `public.artifacts`.
- Rehydrate current API response shape so clients still see `RunDetailResponse.events` and `RunDetailResponse.artifacts`.
- Preserve replay lineage:
  - `parent_run_id`,
  - `replay_source_run_id`,
  - `replay_reason`,
  - child run ids.
- Preserve Trigger callback updates.

Files likely involved:

- `app/db/runs.py`
- `app/db/events.py`
- `app/db/artifacts.py`
- `app/services/run_service.py`
- `app/services/replay_service.py`
- `app/services/run_lifecycle_service.py`
- `app/api/runs.py`
- `app/api/replays.py`
- `app/api/trigger_callbacks.py`
- `tests/db/test_runs_repository.py`
- `tests/api/test_runs.py`
- `tests/api/test_replays.py`
- `tests/api/test_trigger_callbacks.py`

Acceptance:

- Command -> run -> lifecycle callback -> artifact -> replay works the same under both adapters.
- Events and site events remain append-only.

### 1.5 Implement the control-plane adapter switch safely

Needed:

- Replace the `NotImplementedError` in `SupabaseControlPlaneClient` with a real adapter boundary or split repository adapter pattern.
- Keep `control_plane_backend=memory` as default until all Supabase-backed repository/API tests pass.
- Do not let services open SQL/REST directly except through repository modules.

Files likely involved:

- `app/db/client.py`
- all control-plane `app/db/*.py` repositories.

Acceptance:

- `control_plane_backend=supabase` boots without raising before first request.
- No service branches on SQL implementation details.

## 2. Managed-Agent Persistence

This is all durable agent-platform state currently stored in `InMemoryControlPlaneStore` or documented as scaffold-only.

### 2.1 Agent registry and revisions

Needed tables / durable records:

- `agents`
- `agent_revisions`
- revision ids by agent
- stable slug
- owner `org_id`
- visibility
- lifecycle status
- packaging metadata
- host adapter kind/config envelope
- input/output schema
- bound skill ids
- release notes
- compatibility metadata

Files likely involved:

- `app/models/agents.py`
- `app/db/agents.py`
- `app/services/agent_registry_service.py`
- `app/api/agents.py`
- `tests/api/test_agents.py`

Acceptance:

- Agents and revisions survive process restart.
- Sessions remain pinned to the revision they started on.
- Publishing/cloning/archiving semantics remain unchanged.

### 2.2 Skill registry

Needed tables / durable records:

- `skills`
- skill keys
- skill metadata
- input/output contracts
- permission requirements
- skill-to-agent revision binding table if not embedded.

Files likely involved:

- `app/models/skills.py`
- `app/db/skills.py`
- `app/services/skill_registry_service.py`
- `app/api/skills.py`
- `tests/db/test_skills_repository.py`
- `tests/api/test_skills.py`

Acceptance:

- Skills remain reusable across agents.
- Hermes tool discovery can derive from skills/revision policy instead of hardcoded command policy alone.

### 2.3 Sessions, turns, turn events, and compaction summaries

Needed tables / durable records:

- `agent_sessions`
- session events / timeline
- turns
- turn events
- session memory summaries / compaction summaries

Files likely involved:

- `app/models/sessions.py`
- `app/models/session_journal.py`
- `app/models/turns.py`
- `app/db/sessions.py`
- `app/db/turn_events.py`
- `app/services/session_service.py`
- `app/services/turn_runner_service.py`
- `app/services/compaction_service.py`
- `app/api/sessions.py`
- `tests/api/test_sessions.py`
- `tests/services/test_compaction_service.py`

Acceptance:

- Session turn history survives restart.
- Session compaction summaries are durable.
- Turn replay/event append remains scoped by org/business/environment.

### 2.4 Permissions and tool policy

Needed tables / durable records:

- `agent_tool_permissions`
- permission keys `(agent_revision_id, tool_name)`
- modes: `always_allow`, `always_ask`, `forbidden`
- capability flags for tool calls and adapter usage.

Files likely involved:

- `app/models/permissions.py`
- `app/db/permissions.py`
- `app/services/permission_service.py`
- `app/services/hermes_tools_service.py`
- `app/api/permissions.py`
- `tests/api/test_permissions.py`
- `tests/api/test_hermes_tools.py`

Acceptance:

- Tool policy works identically under memory and Supabase.
- Forbidden tools fail closed.
- Always-ask tools create approval gates.

### 2.5 Outcomes / evaluation facts

Needed tables / durable records:

- `outcome_evaluations`
- rubric metadata if needed
- links to org, agent, revision, session, run, and actor.

Files likely involved:

- `app/models/outcomes.py`
- `app/db/outcomes.py`
- `app/services/outcome_service.py`
- `app/api/outcomes.py`
- `tests/api/test_outcomes.py`

Acceptance:

- Outcome facts are separate from transport events.
- Evaluation results can feed release promotion/rollback decisions later.

### 2.6 Operational assets

Needed tables / durable records:

- `agent_operational_assets`
- asset binding records
- connect-later asset metadata
- org/business/environment scope.

Files likely involved:

- `app/models/agent_assets.py`
- `app/db/agent_assets.py`
- `app/services/agent_asset_service.py`
- `app/api/agent_assets.py`
- `tests/api/test_agent_assets.py`

Acceptance:

- Assets and asset bindings survive restart.
- Connect-later semantics remain intact.

## 3. Enterprise Controls Persistence

The enterprise plan lists this as Phase 3. Some prior memories say a non-Supabase enterprise-controls slice existed on earlier branches, but this current branch does not show `app/db/rbac.py`, `app/db/secrets.py`, `app/db/audit.py`, or `app/db/usage.py`. Treat the current checkout as authoritative.

### 3.1 Organizations / memberships / actor context

Needed:

- `organizations`
- `memberships`
- actor/service-account identity records or durable mapping
- org ownership on agents, sessions, permissions, outcomes, assets, runs, commands, approvals, Mission Control projections.

Important rule:

- Add `org_id` without breaking `business_id + environment`.

Acceptance:

- Same `business_id` in two orgs cannot leak data.
- Service-account requests resolve to org-scoped actors.
- Mission Control filters by org first, then business/environment.

### 3.2 RBAC

Needed:

- role grants for:
  - `platform_admin`
  - `org_admin`
  - `agent_builder`
  - `operator`
  - `reviewer`
  - `auditor`
- policy overlay between org role, agent revision policy, and tool permissions.

Acceptance:

- Unauthorized publish/rollback/secret access is blocked.
- Tests cover role deny paths, not just happy paths.

### 3.3 Secrets

Needed:

- secret metadata table.
- secret reference table or provider-backed secret locator.
- binding table from agent revision to named secret references.
- redaction in API models.
- audit events for secret reads/updates/bindings.

Acceptance:

- Raw secret values never return in API responses.
- Agent revisions bind named secret references, not plaintext values.
- Mission Control can show secret health without leaking values.

### 3.4 Append-only audit

Needed:

- audit event table with correlation fields:
  - `org_id`
  - `business_id`
  - `environment`
  - `agent_id`
  - `agent_revision_id`
  - `session_id`
  - `run_id`
  - actor metadata
- events for agent create/publish/archive/clone/rollback, session create, permission updates, secret access, approval actions, host dispatch events, catalog install events.

Acceptance:

- Audit is append-only at DB level.
- Mission Control audit timeline reads from backend-owned audit facts.

### 3.5 Usage accounting

Needed:

- usage event table.
- aggregation paths by org, agent, revision, host adapter, provider, run/session/tool call.
- provider-specific extensibility for Trigger, Codex, Anthropic, local/sandbox.

Acceptance:

- Usage summaries work across more than one host adapter kind.
- Mission Control usage cards read durable usage facts.

## 4. Release Management Persistence

Needed:

- release events table.
- active revision pointer / release channel table.
- canary metadata.
- rollback events.
- replay lineage with revision context.
- evaluation gate records tied to promotions.

Files likely involved:

- `app/models/release_management.py`
- `app/db/release_management.py`
- `app/services/release_management_service.py`
- `app/api/release_management.py`
- `app/services/replay_service.py`
- `app/services/run_lifecycle_service.py`

Acceptance:

- Rollback never rewrites old history.
- Rollback changes active revision through an event + pointer update.
- Replays preserve original and new revision context.
- Evaluation failures can block promotion.

## 5. Mission Control Durable Read Models

Current state:

- Mission Control backend routes exist.
- Current UI uses backend read models and fixtures where needed.
- `mission_control_threads` is still an in-memory projection slot.

Needed:

- Dashboard sourced from canonical durable facts.
- Approvals sourced from durable approval facts.
- Runs sourced from durable run facts.
- Agents/assets sourced from durable agent and asset facts.
- Inbox sourced from one approved durable strategy:
  1. derive directly from contacts/conversations/messages/site_events/tasks/booking_events/sequence_enrollments, or
  2. persist a rebuildable projection table/view.

Rules:

- Do not let the frontend talk directly to Supabase.
- Do not invent frontend-only truth models.
- Prefer Postgres views or rebuildable projection tables over a second source of truth.

Acceptance:

- `/mission-control/dashboard`, `/mission-control/inbox`, `/mission-control/approvals`, `/mission-control/runs`, `/mission-control/agents`, `/mission-control/settings/assets` stay stable.
- Mission Control loads live data in preview/staging without fixture fallback hiding failures.

## 6. Marketing / Lead-Machine Supabase Wiring

Current state:

- Marketing adapter exists and is partially wired.
- Migrations exist for contacts/conversations/site_events/messages/booking_events/sequence_enrollments.
- Memory says a remote contacts insert was smoke-tested.

### 6.1 Contacts / conversations / messages / bookings / tasks / sequences

Needed:

- Finish test coverage for `marketing_backend=supabase` across:
  - lead submit,
  - booking created/cancelled/rescheduled,
  - outbound confirmation/reminder message writes,
  - inbound SMS writes,
  - manual call task creation,
  - non-booker sequence enrollment/status changes.
- Confirm table columns match every model field and metadata field used by current services.
- Confirm `resolve_tenant()` handles slug/numeric business ids correctly.

Acceptance:

- Lease-option happy path can run with `marketing_backend=supabase` without falling back to memory.

### 6.2 Inbound SMS matching risk

Known risk from repo memory:

- Inbound SMS matching is still phone-only.

Needed:

- Add tenant-aware matching using at least:
  - business/environment/org context from webhook routing or provider number,
  - phone number,
  - conversation/channel metadata,
  - fallback handling for ambiguous matches.

Acceptance:

- Same phone number in two tenants does not cross-wire replies.
- Ambiguous inbound SMS fails to review queue rather than picking a random lead like a drunk dartboard.

### 6.3 Sequence guard risk

Known risk from repo memory:

- Sequence guard state is too simplistic for multi-tenant or advanced sequence rollout.

Needed:

- Make sequence enrollment guard state tenant-aware and sequence-aware.
- Preserve unique active enrollment by tenant/contact/sequence.
- Add suppression reason and pause/stop metadata for unsubscribe/reply/bounce/manual override.

Acceptance:

- Duplicate active sequence enrollments cannot happen under Supabase.
- Replied/unsubscribed/bounced leads stop or pause correctly.

### 6.4 Probate lead intake persistence

Current plan says no backend wiring until fixture validation.

Needed after validation:

- Durable tables for probate lead intake, likely:
  - `probate_cases`
  - `probate_leads`
  - `probate_hcad_matches`
  - `lead_scores` or scoring fields
  - ingestion run metadata
  - source raw-file pointers
- Keep keep-now filter stable before persistence.
- Use HCAD account trim/padded acct rule from HCAD memory.

Acceptance:

- A daily/hourly probate pull can persist raw and normalized keep-now records without duplicating cases.
- Mission Control lead queue reads from durable probate lead facts.

### 6.5 Cold-email / Instantly lead automation persistence

Current plans say fixture/provider contract first, no backend wiring until validated.

Needed after validation:

- Durable model for:
  - leads,
  - lead events,
  - automation runs,
  - campaign memberships,
  - tasks,
  - suppression state,
  - cold-email provider metadata,
  - campaign state,
  - mailbox/domain health snapshots,
  - provider webhook events.
- Wire Trigger.dev jobs from TODO:
  - `lead-intake`
  - `instantly-enqueue-lead`
  - `instantly-webhook-ingest`
  - `create-manual-call-task`
  - `followup-step-runner`
  - `suppression-sync`
  - `task-reminder-or-overdue`
- Enforce rule: only `email.sent` creates a manual call task.

Acceptance:

- Instantly/Smartlead/Resend are transport adapters, not the product model.
- Suppression is durable and replay-safe.
- Webhook idempotency prevents duplicate tasks/events.

## 7. Runtime Hardening Persistence / Phase 7

From current enterprise plan Phase 7 and memory: durable checkpoints, persistent memory, stream visibility, sandboxed execution, integration surfaces, and scheduled work remain the next runtime-hardening layer.

### 7.1 Durable checkpoints and resume markers

Needed:

- persistent runtime cursor on sessions/turns/runs.
- enough checkpoint state for `TurnRunnerService` and `RunLifecycleService` to resume after worker restart.
- Mission Control read-model fields for cursor/resume state.

Acceptance:

- Tests prove a run can resume from last durable checkpoint.

### 7.2 Long-term runtime memory

Needed:

- `runtime_memory` model/table/repository/service/API.
- memory scoped by org + business + environment + user/assistant/session where appropriate.
- queryable memory, not one blob.
- separate from session compaction summaries.

Acceptance:

- Cross-session memory lookup works by scoped key.
- Mission Control can display memory context without becoming source of truth.

### 7.3 Live runtime streams

Needed:

- runtime stream/event feed table or durable stream projection.
- route/API for Mission Control polling or streaming.
- correlation with Trigger lifecycle callbacks.

Acceptance:

- Mission Control feed entries show active, failed, completed, and resumed work with explicit lineage.

### 7.4 Sandboxed execution and integration declarations

Needed:

- sandbox adapter durable configuration / capability registration.
- integration declarations for MCP/A2A-style tools and agent handoffs.
- fail-closed behavior for unsupported sandbox/integration configs.

Acceptance:

- Sandbox/integration registration fails closed in tests.
- Adapter-specific config remains isolated from base agent identity.

### 7.5 Scheduled work

Needed:

- scheduling as first-class runtime metadata, even if Trigger.dev remains the scheduler.
- durable scheduled job intent/history records.
- avoid ad hoc cron as hidden business logic.

Acceptance:

- Scheduled work stays under Trigger.dev adapter and is visible in runtime/Mission Control state.

## 8. Catalog / Marketplace Persistence

Needed:

- `catalog` entries referencing agent revisions, not apps.
- installed-agent records or cloned revision records.
- source revision lineage.
- host compatibility requirements.
- required skill and secret binding metadata.
- marketplace readiness flags:
  - `internal`
  - `private_catalog`
  - `marketplace_candidate`
  - `marketplace_published`
- feature flag for public marketplace side.

Acceptance:

- Internal catalog install works before marketplace exposure.
- Trigger-only agents cannot install into incompatible host environments.
- Marketplace flags prevent accidental public launch.

## 9. Environment / Deployment Wiring

Needed:

- Canonical `.env.example` entries, cleaned and current:
  - `RUNTIME_API_KEY`
  - `CONTROL_PLANE_BACKEND`
  - `MARKETING_BACKEND`
  - `SITE_EVENTS_BACKEND`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_DIRECT_CONNECTION_STRING` or pooler URL guidance
  - `TRIGGER_SECRET_KEY`
  - `TRIGGER_API_URL`
  - provider keys for Cal.com, TextGrid, Resend, Instantly/Smartlead.
- Clear setup docs for local MacBook vs hosted preview/staging.
- Supabase CLI project-ref and pooler-url verification steps.
- Migration dry-run / reset / push commands.

Acceptance:

- A future session can tell exactly where Supabase wiring should happen and which environment owns it.
- No one has to reverse-engineer secrets from a cursed `.env.example` blob.

## 10. Suggested Implementation Order

1. **Create a dedicated Supabase wiring branch.**
   - Suggested: `feature/ares-supabase-wiring` or revive/compare `feature/mission-control-supabase-persistence` carefully.
   - Do not mix with current no-wire docs/UI/runtime branch work.

2. **Preflight Supabase target.**
   - Verify project ref, pooler URL, DB password, and current migration history.
   - Use local reset before any remote action.

3. **Schema compatibility decision doc.**
   - Resolve string IDs vs bigint SQL IDs.
   - Resolve enum/timestamp drift.
   - Decide org_id additive strategy.

4. **Runtime core adapter.**
   - commands -> approvals -> runs -> events/artifacts -> replays -> Trigger callbacks.

5. **Managed-agent adapter.**
   - agents/revisions -> skills -> sessions/turns -> permissions -> outcomes -> assets.

6. **Mission Control durable reads.**
   - dashboard/approvals/runs/agents/assets first.
   - inbox projection last because it is easiest to turn into sludge.

7. **Enterprise controls.**
   - org/memberships -> RBAC -> secrets -> audit -> usage.

8. **Marketing lead-machine durability.**
   - finish marketing Supabase tests.
   - fix inbound SMS matching.
   - fix sequence guard.
   - add probate and cold-email persistence only after fixture/provider validation gates.

9. **Runtime hardening.**
   - checkpoints -> runtime memory -> streams -> sandbox/integrations -> scheduled work.

10. **Catalog/install/marketplace.**
    - internal catalog first.
    - marketplace later behind flags.

## 11. Minimum Test Gates

Before claiming Supabase wiring is done:

```bash
supabase db reset --local
uv run pytest tests/db/test_commands_repository.py tests/db/test_approvals_repository.py tests/db/test_runs_repository.py -q
uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py -q
uv run pytest tests/api/test_agents.py tests/api/test_sessions.py tests/api/test_permissions.py tests/api/test_outcomes.py tests/api/test_agent_assets.py tests/api/test_hermes_tools.py -q
uv run pytest tests/api/test_mission_control.py -q
uv run pytest -q
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npx tsc -p trigger/tsconfig.json --noEmit
```

For remote rollout:

```bash
supabase db push --dry-run --linked
supabase migration list --linked
```

If linked mode fails, use the exact repo-local pooler URL and password flow from the Supabase recovery runbook. Do not keep retrying the same broken command like a Roomba hitting a chair leg.

## 12. Do-Not-Do List

- Do not edit already-applied baseline migrations in place.
- Do not switch `control_plane_backend=supabase` until the adapter exists and tests pass.
- Do not bypass FastAPI by letting Mission Control frontend call Supabase directly.
- Do not duplicate durable truth in Mission Control projection tables unless they are rebuildable.
- Do not remove `business_id + environment` during org migration.
- Do not perform production remote migration from this environment without explicit approval.
- Do not mix Supabase cutover with UI contract fixes, enterprise backlog cleanup, or provider rewrites.
- Do not treat Trigger.dev, Instantly, Smartlead, Resend, Cal.com, or TextGrid as the product model. They are adapters/transports.

## 13. Open Questions To Resolve Before Coding

1. What Supabase project is the target for the next wiring pass: existing `awmsrjeawcxndfnggoxw`, a preview/staging project, or a new fresh project?
2. Should the current branch resurrect artifacts from `origin/feature/mission-control-supabase-persistence`, or should those be used only as reference while writing fresh additive migrations?
3. What is the canonical ID strategy for prefixed runtime IDs vs bigint SQL primary keys?
4. Should org tenancy land before or after runtime core persistence in the actual implementation branch?
5. Should `site_events_backend` default to `memory` for local dev to prevent missing Supabase creds from breaking unrelated work?
6. What exact cold-email provider gets first durable integration: Instantly or Smartlead?
7. What is the first live lead-machine dataset to persist after Supabase core: lease-option submissions, probate keep-now leads, or cold-email campaign state?

## One-Line Current Truth

Ares has a useful in-memory runtime, partial marketing/site-event Supabase wiring, and baseline SQL. The remaining Supabase work is the full durable control-plane + managed-agent + Mission Control + enterprise/runtime-hardening cutover, done additively and gated through local/staging before production.
