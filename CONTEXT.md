# Context
## Stable Facts

- Repo: `/Users/solomartin/Projects/Ares`
- Purpose: reusable operating runtime and control plane that agent drivers call into
- Source of truth:
  - `CONTEXT.md` = branch router / current scope
  - `memory.md` = indexed master memory

## Current Scope

1. branch: `feature/mission-control-enterprise-backlog`
2. treat `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md` as the canonical execution plan for this branch
3. treat these as live source inputs:
   - `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
   - `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
4. build on current `main`; do not re-do already landed Ares CRM / lead-machine phases
5. preserve existing Supabase wiring and extend it additively
6. keep the product model explicit:
   - agents are the product unit
   - Mission Control is the operator cockpit
   - skills are reusable procedures
   - host runtimes are adapters
7. current backlog focus after the merged baseline:
   - org tenancy + actor context
   - agent deployment / host adapters
   - enterprise controls
   - release lifecycle
   - Mission Control productization
   - internal catalog later

## Current TODO

1. continue Phase 6 bounded Mission Control productization slices on `feature/mission-control-enterprise-backlog`
2. keep replay lineage, release management, and Mission Control productization separated by slice
3. avoid Supabase/migration work unless a later slice explicitly requires it

## Recent Change

- 2026-04-22: Phase 6 slice P6.1 makes agents the first-class Mission Control navigation/work surface in the fixture-backed UI only: lead-machine and marketing now default to agent-centered pages, approvals are promoted into the nav beside dashboard/inbox/runs, and the shell/agent page copy explicitly frames the rest of Mission Control as operator views around agents without starting detail pages or adding Phase 6 control surfaces.
- 2026-04-22: P5.3 replay-lineage blocker repair keeps replay execution on replay-owned command records instead of reusing the original command identity, preserves the original command/run binding, persists approval-path replay metadata through the approval snapshot, and binds replay child lineage only when a replay approval is later approved so child runs retain truthful parent/reason/actor lineage without Supabase schema work.
- 2026-04-22: Phase 5 slice P5.3 upgrades replay lineage in the runtime only: replay responses now carry triggering actor plus source/replay revision context, replay events are appended through `run_lifecycle_service` onto parent/child runs instead of mutating worker-owned state, and release context is derived from immutable release-management events so historical replays stay pinned to the original revision while still exposing the current release context after supersede/rollback; eval gating and Mission Control UI/read-model work stay deferred.
- 2026-04-22: Phase 5 slice P5.2 adds a bounded runtime-owned release-management domain with immutable release-event records, dedicated publish/rollback routes, legacy `/agents` publish now funneled through release-event emission, active-archive fail-closed on the legacy path, and rollback now clones the historical target into a new published revision so deprecated history stays immutable while replay remains pinned to original revision ids; replay lineage, evaluation gates, and Mission Control UI wiring stay deferred.
- 2026-04-22: Phase 5 slice P5.1 expands agent revision semantics with additive `candidate` and `deprecated` states, keeps rollback/rolled_back deferred to later release-event work, adds per-revision `release_channel` metadata that round-trips through create/publish/clone, preserves org/business/environment scoping, and now deprecates superseded published revisions instead of auto-archiving them.
- 2026-04-22: Phase 4 slice P4.5 adds a read-only org-scoped `GET /mission-control/settings/governance` bundle for pending approvals, internally-derived active-revision secrets health, recent audit, and usage summary/recent usage without hitting secret read paths that emit audit noise, and wires the native Mission Control Settings shell to render that governance snapshot with thin frontend coverage.
- 2026-04-22: Phase 4 slice P4.3 hardens raw `/audit` behind trusted actor-context org/actor derivation with 422-on-conflict behavior, scopes audit reads to the caller org by default, scrubs sensitive metadata on append and read, and now persists deterministic equal-timestamp append order through the audit model's own monotonic `updated_at` field without touching Supabase wiring.
- 2026-04-22: Phase 4 slice P4.2 hardens secret binding integrity against real revision/org/declared-secret refs, keeps public secret responses metadata-only/redacted, validates revision existence on the revision-bindings read path, and emits `secret_accessed` audit events from the existing secrets service seam for secret list/binding reads without touching Supabase wiring or widening the audit design.
- 2026-04-22: Phase 4 slice P4.1d closes the final RBAC runtime blocker by collapsing semantically duplicate canonical-ish legacy assigned roles into one logical effective-permission source, conservatively combining duplicate grants under a stable canonical source label while leaving unknown legacy roles read-safe and untouched.
- 2026-04-22: Phase 4 slice P4.1c closes the final RBAC backward-compat blocker by collapsing semantically duplicate canonical-ish legacy stored roles into one logical role for list/get/create behavior, deterministically selecting the surviving record, and keeping strict canonical validation for new input without touching Supabase wiring.
- 2026-04-22: Phase 3 slice P3.5 makes Hermes tools revision-aware from bound skill data by deriving the visible command surface from bound skills' `required_tools`, falling back open when skills contribute no supported Hermes commands, and rejecting out-of-surface command invocations with `403` while preserving existing permission/RBAC/capability enforcement and runtime dispatch behavior.
- 2026-04-22: Phase 3 slice P3.4c closes the agent-backed replay gap by deriving replay `agent_revision_id` from the parent run's host-adapter dispatch correlation, routing child safe-autonomous replays back through the adapter seam, and failing replay cleanly with `422` when the original revision is no longer dispatchable.
- 2026-04-22: Phase 3 slice P3.4b restores idempotent dedupe for agent-backed safe-autonomous commands by checking existing command records before dispatchability validation, so archived/disabled revision retries return the original command/run while brand-new invalid requests still fail closed without queued orphans.
- 2026-04-22: Phase 3 slice P3.4a now preserves `agent_revision_id` through Hermes tool invocation, pre-validates safe-autonomous agent-backed dispatchability through `agent_execution_service` before command/run persistence, fails closed for missing/draft/archived/disabled revisions, and keeps host-adapter dispatch correlation anchored to `run.id` without touching approval-path or Supabase wiring.
- 2026-04-22: Phase 3 slice P3.3 hardened the in-memory host-adapter contract with explicit dispatch/status-correlation/artifact/cancellation interfaces, richer adapter read-model metadata, duplicate-registry guards, and focused host-adapter coverage without touching Supabase wiring.

## Read These Sections In `memory.md`

1. `## Current Direction`
2. `## Runtime Architecture`
3. `## Current Runtime Surface`
4. `## Open Work`
5. latest entry in `## Change Log`
