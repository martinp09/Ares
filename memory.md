# Memory

> This is the master memory file. Keep it indexed and durable. Do not load the whole file by default.

## How To Use This File

- Start in `CONTEXT.md`
- Read only the sections referenced there unless the task clearly requires more
- Record durable architecture decisions, environment notes, open work, and major change history here

## Memory Index

- Current priorities:
  - `## Current Direction`
  - `## Open Work`
- Repo conventions:
  - `## Repo Conventions`
- Environment and infra:
  - `## Environment Notes`
- Architecture:
  - `## Runtime Architecture`
  - `## Hermes Integration`
- Migration:
  - `## Migration Strategy`
- Recent work:
  - latest entry in `## Change Log`

## Current Direction

- Hermes is the current primary control shell and browser-capable driver
- This repo should become the reusable real-estate operating runtime those drivers call into
- Generalist runtime first, lanes and strategies second
- Real estate is the first optimization target
- Marketing control plane is the first execution domain
- Ares North Star: self-hosted operating system for distressed real-estate lead management
- Source-of-truth implementation plan for phased Ares scope: `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md`
- Combined Mission Control + enterprise backlog execution plan: `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md`
- Mission Control orchestration plan remains a live source input: `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- Enterprise agent platform plan remains a live source input: `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- Phase 1 county baseline stays explicit: Harris, Tarrant, Montgomery, Dallas, Travis
- Phase 1 lead rule stays explicit: probate-first with tax-delinquency overlay
- Phase 1 outreach rule stays explicit: drafts require human approval before send
- The runtime must cover data gathering, prospecting, acquisitions, transaction coordination, title, and dispo
- Source lanes, strategy lanes, and operational stages must stay separate concepts
- The current MVP path is a two-lane cut:
  - outbound probate as source lane with cold email as outbound method
  - inbound lease-option marketing as a separate first-class lane
- Supabase should be the canonical backend for both live MVP lanes
- The runtime should preserve a thin contract-to-close skeleton even while the MVP stays focused on lead intake, outreach, replies, and operator handoff
- Mission Control stays fixture-backed until the live backend slice is intentionally enabled later
- The host-adapter/skill seam is now in-memory and additive, with trigger_dev as the default enabled adapter; dispatch requires published revisions and preserves per-revision host adapter config
- Phase-0 docs now lock the product model: agents are the product unit, skills are reusable procedures, host runtimes are adapters, and Mission Control is the operator cockpit

## Repo Conventions

- `memory.md` is the master memory
- `CONTEXT.md` stays short and points into this file
- `WAT_Architecture.md` defines the operating model
- Keep hard guarantees in code, not in prompts

## Environment Notes

- Fresh Supabase project created for Hermes Central Command
- Local `.env` should be ported from the validated `Mailers AWF` environment as needed
- GitHub owner: `martinp09`
- Planned local path: `/Users/solomartin/Projects/Hermes Central Command`
- Trigger.dev CLI login is configured on this machine
- `TRIGGER_SECRET_KEY` is present in the local `.env`
- Trigger.dev local worker boot verified against project `proj_puouljyhwiraonjkpiki`
- Local `.env` already includes `Cal.com`, `TextGrid`, and `Resend` credentials needed for the lease-option MVP
- The active landing page lives at `/Users/solomartin/Business/website/lease-options-landing`
- The landing page currently persists form submissions and redirects to `Cal.com`, but still hands automation off to `n8n`
- A proven `TextGrid` adapter exists in `/Users/solomartin/Projects/Phone System/api/_lib/providers/textgrid.js`

## Runtime Architecture

- FastAPI runtime for typed commands and policy
- Trigger.dev for durable jobs
- Supabase for canonical state and audit
- Hermes-facing tool/API surface

## Current Runtime Surface

- FastAPI routes currently mounted:
  - `GET /health`
  - `POST /commands`
  - `POST /approvals/{approval_id}/approve`
  - `GET /runs/{run_id}`
  - `POST /replays/{run_id}`
  - `GET /hermes/tools`
  - `POST /hermes/tools/{tool_name}/invoke`
  - `POST /skills`
  - `GET /skills`
  - `GET /skills/{skill_id}`
  - `POST /agents`
  - `GET /agents/{agent_id}`
  - `POST /agents/{agent_id}/revisions/{revision_id}/publish`
  - `POST /agents/{agent_id}/revisions/{revision_id}/archive`
  - `POST /agents/{agent_id}/revisions/{revision_id}/clone`
  - `POST /organizations`
  - `GET /organizations`
  - `GET /organizations/{org_id}`
  - `POST /memberships`
  - `GET /memberships`
  - `GET /memberships/{membership_id}`
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
  - `GET /mission-control/lead-machine`
  - `GET /mission-control/inbox`
  - `GET /mission-control/tasks`
  - `GET /mission-control/runs`
  - `POST /marketing/webhooks/calcom`
  - `POST /marketing/webhooks/textgrid`
  - `POST /marketing/internal/non-booker-check`
  - `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
  - `POST /ares/run`
  - `POST /site-events`
  - `POST /trigger/callbacks/runs/{run_id}/started`
  - `POST /trigger/callbacks/runs/{run_id}/completed`
  - `POST /trigger/callbacks/runs/{run_id}/failed`
  - `POST /trigger/callbacks/runs/{run_id}/artifacts`
- Current storage mode:
  - hybrid mode:
    - Supabase-backed adapters for marketing, lead-machine, opportunities, and shared command/run lifecycle records (`commands`, `approvals`, `runs`, `events`, `artifacts`) when enabled
    - the remaining shared control-plane runtime now uses a Supabase-backed hydrated transaction store for:
      - agents / revisions
      - sessions / memory summaries
      - turns / turn events
      - permissions / RBAC / secrets
      - audit / usage / outcomes
      - agent assets / Mission Control threads / skills / host adapter dispatches
    - in-memory fallback still remains for tests and local fixture-first work
- Current workflow coverage:
  - marketing command classification
  - Hermes tool contract with permission-aware tool gating
  - replay safety API
  - Trigger marketing worker chain scaffold
  - landing-page site-event forwarding contract
  - managed-agent revision/session/outcome/asset scaffolding without live Supabase wiring
  - in-memory organization directory + org membership scaffolding for dogfood tenancy
  - probate intake -> scoring -> bridge -> enqueue -> webhook -> suppression/task loop
  - lease-option submit -> booking webhook -> SMS/manual-call loop
  - additive Mission Control workspaces for `Lead Machine`, `Marketing`, and `Pipeline`

## Hermes Integration

- Hermes handles chat, approvals, coordination, and operator UX
- Hermes should not be treated as the source of truth
- Every Hermes action should map to a typed runtime command

## Migration Strategy

- Start fresh on new Supabase and new runtime repo
- Build marketing control plane first
- Defer seller-ops migration off `n8n` until runtime backbone exists

## Open Work

1. keep Phase 6 closed through `P6.5` unless a fresh blocker appears
2. treat Phase 7 (`P7.1` + `P7.2` + `P7.3`) as implemented, QC-fixed, and locally verified; the next step is commit/push for the combined diff
3. keep browser acquisition and ambiguous research in Hermes or other driver agents, not inside Ares
4. add durable Trigger lead-machine jobs only where sync paths become operationally risky
5. keep `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md` and `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md` as live source inputs for this branch scope

## Change Log

### 2026-04-23 Phase 7 QC Fix Follow-up

- Closed the two Phase 7 QC findings without widening scope:
  - `marketplace_publication_enabled` now derives live from config at read time instead of being persisted as stale point-in-time truth in catalog records
  - Mission Control catalog install copy now speaks in terms of selected target scope, and install success messaging explicitly reports when the install landed outside the current filtered view
- Updated `app/models/catalog.py`, `app/db/catalog.py`, and `app/services/catalog_service.py` so catalog responses keep visibility metadata truthful even if the marketplace-publication gate flips after the entry was created.
- Updated `apps/mission-control/src/App.tsx`, `apps/mission-control/src/pages/CatalogPage.tsx`, `apps/mission-control/src/components/AgentInstallWizard.tsx`, and related frontend tests so scope-switch/install messaging stays honest and same-scope installs still refresh the visible agents surface.
- Added/updated regressions in `tests/api/test_catalog.py`, `tests/db/test_catalog_repository.py`, `apps/mission-control/src/App.test.tsx`, and `apps/mission-control/src/pages/CatalogPage.test.tsx`.
- Verified with `npm --prefix apps/mission-control run test -- --run src/App.test.tsx src/pages/CatalogPage.test.tsx src/lib/api.test.ts` (`32 passed`), `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `59 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/db/test_catalog_repository.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` (`24 passed`), and `./.venv/bin/python -m pytest -q` (`469 passed, 5 warnings`).

### 2026-04-23 Phase 7 Slice P7.3 Marketplace Readiness Flags

- Added a fail-closed marketplace publication gate in `app/core/config.py` + `app/services/agent_registry_service.py`: `marketplace_published` is now blocked by default unless `marketplace_publish_enabled` is explicitly turned on, so public launch cannot happen by accident.
- Extended catalog metadata in `app/models/catalog.py`, `app/db/catalog.py`, and `app/services/catalog_service.py` so catalog entries now expose source-agent visibility plus a derived `marketplace_publication_enabled` flag while remaining org-scoped internal catalog records.
- Updated Mission Control catalog mapping + UI (`apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/lib/fixtures.ts`, `apps/mission-control/src/pages/CatalogPage.tsx`) so operators can see listing visibility and whether public launch is still disabled without implying an actual marketplace rollout.
- Added focused regressions for the new gate + metadata in `tests/api/test_agents.py`, `tests/api/test_catalog.py`, `tests/api/test_agent_installs.py`, `tests/db/test_catalog_repository.py`, `apps/mission-control/src/lib/api.test.ts`, and `apps/mission-control/src/pages/CatalogPage.test.tsx`.
- Verified with `./.venv/bin/python -m pytest tests/api/test_catalog.py tests/api/test_agent_installs.py -q` (`6 passed`), `./.venv/bin/python -m pytest tests/api/test_agents.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/db/test_catalog_repository.py -q` (`23 passed`), `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `58 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `./.venv/bin/python -m pytest -q` (`468 passed, 5 warnings`).

### 2026-04-23 Phase 7 Slice P7.2 Catalog UI

- Added `apps/mission-control/src/pages/CatalogPage.tsx`, `apps/mission-control/src/components/AgentInstallWizard.tsx`, and `apps/mission-control/src/pages/CatalogPage.test.tsx` to expose the internal catalog as a bounded Mission Control surface on top of the already-landed `P7.1` backend APIs.
- Updated `apps/mission-control/src/App.tsx`, `apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/lib/fixtures.ts`, `apps/mission-control/src/App.test.tsx`, and `apps/mission-control/src/lib/api.test.ts` so the shell can fetch catalog entries, install a selected entry into the current runtime scope, and keep the UI truthful about org scope + fallback state.
- Closed the main truthfulness risks discovered during review:
  - fixture-backed catalog entries are visible for dogfood inspection but installs are disabled until `/catalog` is live again
  - catalog entries now carry `orgId`, are normalized to the selected org scope, and neutralize outside the internal org instead of leaking internal fixtures
  - install success/failure writes are dropped when the operator changes scope mid-request
- Added focused regressions covering catalog mapping/install behavior, fixture-backed install disabling, and org-scope neutralization in `apps/mission-control/src/App.test.tsx`, `apps/mission-control/src/lib/api.test.ts`, and `apps/mission-control/src/pages/CatalogPage.test.tsx`.
- Verified with `npm --prefix apps/mission-control run test -- --run` (`20 files passed`, `58 tests passed`), `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, and `./.venv/bin/python -m pytest -q` (`465 passed, 5 warnings`).

### 2026-04-23 Phase 7 Slice P7.1 Catalog Domain (backend/domain)

- Added `app/models/catalog.py`, `app/models/agent_installs.py`, `app/db/catalog.py`, `app/db/agent_installs.py`, `app/services/catalog_service.py`, `app/services/agent_install_service.py`, `app/api/catalog.py`, and `app/api/agent_installs.py` for the first bounded internal catalog/install domain.
- Updated `app/db/client.py` and `app/main.py` so the in-memory control-plane store now tracks catalog entries + install lineage and the new routers are mounted behind the existing runtime API-key guard.
- Kept execution semantics stable by making installs reuse the existing agent-creation contract: catalog entries point at agent revisions with derived host/provider/skill/secret/release compatibility metadata, while installs create new agent/revision records plus a first-class install lineage record instead of adding a parallel runtime path.
- Added focused repository/API coverage in `tests/db/test_catalog_repository.py`, `tests/db/test_agent_install_repository.py`, `tests/api/test_catalog.py`, and `tests/api/test_agent_installs.py`.
- Verified with `./.venv/bin/python -m pytest tests/db/test_catalog_repository.py tests/db/test_agent_install_repository.py tests/api/test_catalog.py tests/api/test_agent_installs.py tests/api/test_agents.py -q` (`21 passed`) and `./.venv/bin/python -m pytest -q` (`460 passed, 5 warnings`).

### 2026-04-23 Phase 6 Completion Through P6.5 (QC-approved)

- Closed the remaining Phase 6 Mission Control slices on the active non-Supabase path:
  - `P6.3` added release/host visibility through `AgentReleasePanel`, `HostAdapterBadge`, and the agents-first shell wiring
  - `P6.4` added read-only governance surfaces for secrets health, audit, usage, and settings
  - `P6.5` added org-aware navigation/filtering with an `OrgSwitcher`, org-scoped API headers, secondary `business_id` / `environment` request scoping, and bounded fallback truth-gating
- Updated `app/services/organization_service.py` so the internal/default operator path can enumerate seeded orgs while non-internal actors remain self-scoped, preserving the non-Supabase tenancy seam.
- Updated the Mission Control frontend (`apps/mission-control/src/App.tsx`, `apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/pages/InboxPage.tsx`, and related tests/components) so:
  - scope switches neutralize prior-scope inbox/agent content while the next org/business/environment load is in flight
  - fallback data still respects secondary business/environment filters
  - org-only fixture fallback now fails neutral for dashboard/inbox/tasks/approvals/settings surfaces instead of relabeling internal fixture truth under another org
  - settings assets now re-fetch on scoped `business_id` / `environment` changes because the cache key matches the scoped request contract
- Expanded `tests/api/test_mission_control.py`, `tests/api/test_organizations.py`, `tests/services/test_mission_control_service.py`, `apps/mission-control/src/App.test.tsx`, `apps/mission-control/src/lib/api.test.ts`, `apps/mission-control/src/components/OrgSwitcher.test.tsx`, `apps/mission-control/src/components/MissionControlShell.test.tsx`, and `apps/mission-control/src/pages/InboxPage.test.tsx` with focused regressions for org-aware scope switching, neutral pending states, scoped fallback filtering, and settings asset re-scoping.
- Verified the final Phase 6 branch state with:
  - `npm --prefix apps/mission-control run test -- --run` (`19 files passed`, `52 tests passed`)
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run build`
  - `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest tests/api/test_mission_control.py tests/api/test_agents.py tests/api/test_release_management.py tests/api/test_organizations.py tests/services/test_mission_control_service.py -q` (`53 passed`)
  - `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest -q` (`458 passed, 5 warnings`)
- Fresh `gpt-5.4` XHIGH QC approved the current `P6.5` diff with no remaining blocker-level findings.

### 2026-04-23 Phase 6 Slice P6.2 Read-Only Agent Detail Workflow (QC-approved)

- Added the first bounded Mission Control agent-detail surface via `apps/mission-control/src/pages/AgentDetailPage.tsx`, wired from the agents-first workspace through `apps/mission-control/src/App.tsx` and `apps/mission-control/src/components/AgentRegistryTable.tsx`, while keeping the slice strictly read-only with no publish/rollback controls.
- Expanded the frontend Mission Control data seam in `apps/mission-control/src/lib/api.ts` plus fixtures/tests so the detail page can project revisions, release history, secrets health, recent audit, usage, and turns, and so partial auxiliary failures now mark degraded sections explicitly instead of silently pretending empty-state truth.
- Closed the remaining truthfulness blockers in the final pass:
  - the side context panel now uses the same loading/id-match truth gate as the main detail pane and no longer risks stale detail during agent switching
  - degraded root-detail fallback now preserves summary `slug`, `description`, `businessId`, `createdAt`, and `updatedAt`, while leaving lifecycle truth unavailable unless the summary actually provides it
  - shell-level `statusBadge` / `footerNote` now reconcile after agents-surface recovery instead of lagging behind stale fixture-fallback state
- Added focused regressions in `apps/mission-control/src/App.test.tsx` and `apps/mission-control/src/lib/api.test.ts` covering context-panel loading neutrality, degraded summary-truth preservation, lifecycle-truth non-fabrication, and shell/source reconciliation after agents recovery.
- Verified the closed slice with `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, `npm --prefix apps/mission-control run build`, `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest tests/api/test_mission_control.py tests/api/test_agents.py tests/api/test_release_management.py -q`, and `/Users/solomartin/Projects/Ares/.venv/bin/python -m pytest -q` (`25 frontend tests passed`, `40 targeted backend tests passed`, `452 passed, 5 warnings` full backend suite).
- Fresh `gpt-5.4` XHIGH QC approved the current `P6.2` diff with no remaining blocker-level findings.

### 2026-04-22 Phase 6 Slice P6.1 Agents-First Mission Control Navigation

- Updated `apps/mission-control/src/App.tsx`, `apps/mission-control/src/components/MissionControlShell.tsx`, and `apps/mission-control/src/pages/AgentsPage.tsx` so lead-machine and marketing now default to agent-centered pages, the shell copy explicitly frames agents as the product unit, and approvals/runs sit beside dashboard/inbox as operator views around agents without introducing P6.2 detail pages or new control surfaces.
- Added bounded UI-only glue for agent/operator-view cards plus approvals navigation, keeping the no-Supabase path intact and preserving the existing fixture/live read-model wiring.
- Expanded `apps/mission-control/src/App.test.tsx`, `apps/mission-control/src/components/MissionControlShell.test.tsx`, and `apps/mission-control/src/pages/AgentsPage.test.tsx` with failing-first coverage for the agents-first IA, adjacent operator-view summaries, and approvals visibility.
- Verified with `npm --prefix apps/mission-control run test -- --run`, `npm --prefix apps/mission-control run typecheck`, and `npm --prefix apps/mission-control run build`.

### 2026-04-22 Phase 5 Slice P5.3 Replay Lineage Blocker Repair

- Added `app/services/replay_lineage_service.py` and refactored replay lineage derivation there so both immediate replays and later-approved replay approvals reuse the same actor/revision/release-context logic while keeping replay/source revision ids pinned to the historical parent run.
- Updated `app/services/replay_service.py` to create replay-owned command records with fresh idempotency keys before dispatch or approval creation, eliminating reuse of the original command identity and preserving the original command's `run_id`.
- Updated `app/services/approval_service.py` and `app/services/run_lifecycle_service.py` so replay approvals persist lineage metadata inside the existing approval payload snapshot, approved replay children are created with `parent_run_id`/`replay_reason`, and child-only `replay_lineage_bound` events are appended at approval time without duplicating the parent replay-request event.
- Expanded `tests/api/test_replays.py` and `tests/api/test_approvals.py` with failing-first regressions proving replay no longer overwrites the original command/run binding and approval-required replay later creates a distinct child run with preserved replay lineage bound on approval.
- Verified with `./.venv/bin/python -m pytest tests/api/test_replays.py tests/api/test_approvals.py -q` (`9 passed`; failing-first repro was `2 failed, 7 passed`).

### 2026-04-22 Phase 5 Slice P5.3 Replay Lineage Upgrade

- Updated `app/models/runs.py`, `app/services/replay_service.py`, `app/services/run_lifecycle_service.py`, and `app/api/replays.py` so replay responses now carry runtime-owned lineage models with triggering actor metadata plus separate source/replay revision context.
- Reused the bounded release-management domain instead of adding new persistence: replay lineage derives source release context from the latest immutable release event affecting the parent revision at the parent run timestamp, and derives replay release context from the latest immutable agent release event at replay time.
- Replaced direct parent-run event mutation in replay handling with append-only runtime events written through `run_lifecycle_service`, emitting `replay_requested` on the parent run and `replay_lineage_bound` on the child run when a replay is dispatched.
- Expanded `tests/api/test_replays.py` with failing-first assertions for triggering actor capture, release-channel/event lineage, and preserving original-vs-current release context after clone-based rollback while keeping child dispatch pinned to the original revision id.
- Verified with `./.venv/bin/python -m pytest tests/api/test_replays.py -q` (`6 passed`; failing-first repro was `2 failed, 4 passed`).

### 2026-04-22 Phase 5 Slice P5.2 Release Management Domain

- Added `app/models/release_management.py`, `app/db/release_management.py`, `app/services/release_management_service.py`, and `app/api/release_management.py` to introduce a bounded release-management surface with immutable `publish`/`rollback` event records plus dedicated org-scoped list/publish/rollback routes.
- Extended `app/db/client.py` and `app/main.py` additively so the in-memory control-plane store now tracks release events per agent and the new router is mounted behind the existing runtime API-key guard.
- Repaired the rollout blockers by making rollback clone the requested historical revision into a fresh published revision instead of reactivating a deprecated row in place, keeping the rollback target recorded on the event while old revision ids remain stable for replay/session pinning.
- Routed legacy `/agents/{agent_id}/revisions/{revision_id}/publish` through the release-management service so publish history is no longer bypassable, and made legacy active-archive fail closed until a matching release-event transition exists.
- Expanded `tests/db/test_release_management_repository.py`, `tests/api/test_release_management.py`, `tests/api/test_agents.py`, and `tests/api/test_replays.py` with failing-first coverage for clone-based rollback semantics, legacy publish event emission, fail-closed active archive, and replay staying pinned to the original revision id across supersede + rollback transitions.
- Verified with `./.venv/bin/python -m pytest tests/db/test_release_management_repository.py tests/api/test_release_management.py tests/api/test_agents.py tests/api/test_replays.py -q` (`24 passed`; failing-first repro was `5 failed, 19 passed`).

### 2026-04-22 Phase 5 Slice P5.1 Revision Lifecycle + Release Channel Metadata

- Updated `app/models/agents.py` so revision state now supports `draft`, `candidate`, `published`, `deprecated`, and `archived`, while keeping rollback/rolled_back semantics intentionally deferred to a later release-event slice.
- Updated `app/db/agents.py` so new revisions persist a `release_channel`, draft revisions can move into `candidate`, publishing a newer revision deprecates the previously active published revision instead of auto-archiving it, deprecated revisions fail closed on republish, archive/clone now recompute lifecycle status from the remaining non-archived revisions, and clone preserves the source release channel.
- Updated `app/services/agent_registry_service.py` to pass through `release_channel`, expose an internal candidate-promotion service seam, and prefer the latest non-archived revision when deriving revision state for read models.
- Expanded `tests/api/test_agents.py` with failing-first coverage for default/custom `release_channel` round-tripping and the richer publish transition where superseded revisions become `deprecated` and cannot be republished.
- Expanded `tests/db/test_agents_repository.py` with failing-first coverage for draft→candidate promotion, deprecated republish rejection, and the lifecycle fallback to `deprecated` when the latest published revision is archived but an older deprecated revision remains.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_agents_repository.py tests/api/test_agents.py -q` (`17 passed`; failing-first repro was `5 failed, 12 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_agents.py -q` (`14 passed`)

### 2026-04-22 Phase 4 Slice P4.5 Mission Control Governance Surface

- Added `MissionControlGovernanceResponse` plus active-revision secrets-health summaries in `app/models/mission_control.py`, keeping the slice read-only and focused on approvals, secrets health, audit, and usage.
- Updated `app/services/mission_control_service.py` with `get_governance()` and an internal secrets-health projection that derives org-scoped status directly from active revision metadata, secret bindings, and stored secrets instead of calling secret read paths that append `secret_accessed` audit events.
- Updated `app/api/mission_control.py` to expose `GET /mission-control/settings/governance` as the single org-scoped governance bundle endpoint.
- Expanded `tests/api/test_mission_control.py` with failing-first coverage proving the new endpoint scopes approvals/audit/usage to the caller org, ignores draft-only secret declarations, and does not introduce governance-read `secret_accessed` audit noise.
- Updated the native Mission Control shell (`apps/mission-control/src/lib/api.ts`, `apps/mission-control/src/App.tsx`, `apps/mission-control/src/pages/SettingsPage.tsx`, `apps/mission-control/src/lib/fixtures.ts`, `apps/mission-control/src/App.test.tsx`) so Settings now reads and renders the governance snapshot with a thin read-only surface while preserving existing asset status.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_mission_control.py -q` (`19 passed`; failing-first repro was `1 failed, 18 deselected` for the new governance test)
  - `npm --prefix apps/mission-control run test -- --run src/App.test.tsx` (`4 passed`)
  - `npm --prefix apps/mission-control run typecheck` (`passed`)

### 2026-04-22 Phase 4 Slice P4.3 Audit Trust, Ordering, and Scrubbing

- Updated `app/api/audit.py` so raw `/audit` now uses trusted actor context on both write and read paths: POST derives `org_id`, `actor_id`, and `actor_type` from actor headers/default context and fails with `422` on conflicting body values, while GET defaults to the caller org and rejects mismatched `org_id` queries with `422`.
- Updated `app/services/audit_service.py` to centralize actor-scoped org resolution, populate server-side default actor metadata when append callers omit it, scrub sensitive audit metadata before persistence/response, and keep read-path scrubbing in place for defense in depth.
- Updated `app/models/audit.py` and `app/db/audit.py` so audit records now own a persisted monotonic `updated_at` field, backfill legacy hydrated rows to `created_at` when the field is absent, and sort newest-first by `(created_at, updated_at)` so equal-timestamp append order survives generic text-table persistence/hydration.
- Expanded `tests/db/test_audit_repository.py` with a failing-first regression that round-trips identical-timestamp audit payloads through persisted `updated_at` ordering and proves the latest append still wins after hydration.
- Expanded `tests/api/test_audit.py` with failing-first coverage for trusted actor/org derivation, org-scoped audit reads, append/read metadata redaction, and `422` rejection for conflicting `org_id`/`actor_id`/`actor_type` body values.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_audit_repository.py tests/api/test_audit.py -q` (`7 passed`; failing-first repro was `1 failed, 6 passed`)

### 2026-04-22 Phase 4 Slice P4.2 Secret Binding Integrity + Read Audit

- Updated `app/db/secrets.py` so `bind_secret()` now fails closed unless the target secret exists, the target agent revision exists, the revision's owning agent belongs to the same org as the secret, and the requested `binding_name` is declared in `revision.compatibility_metadata["requires_secrets"]`; existing `(revision_id, binding_name)` dedupe/rebind behavior remains intact.
- Updated `app/services/secrets_service.py` to keep returning `SecretSummaryRecord` public read models, validate revision existence before listing revision bindings, and emit `secret_accessed` audit events through the existing `audit_service.append_event()` seam for secret-list and revision-binding read paths without logging plaintext values.
- Updated `app/api/secrets.py` to map secret endpoint validation errors consistently: not-found failures return `404`, while fail-closed declared-ref validation returns `422`.
- Expanded `tests/db/test_secrets_repository.py` with failing-first coverage for missing revision, foreign-org revision, undeclared binding-name rejection, and preserved dedupe/rebind behavior.
- Expanded `tests/api/test_secrets.py` with failing-first coverage for redacted public responses, secret read-path audit emission, missing/undeclared/foreign binding rejection, and missing revision validation on `/secrets/revisions/{revision_id}`.
- Updated the affected Mission Control secret-surface regression in `tests/api/test_mission_control.py` so published test agents explicitly declare the secret refs they bind.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_secrets_repository.py tests/api/test_secrets.py -q` (`7 passed`; failing-first repro was `6 failed, 1 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_mission_control.py -q -k secret_audit_and_usage_endpoints_scope_to_actor_org` (`1 passed, 17 deselected`)

### 2026-04-22 Phase 4 Slice P4.1d RBAC Runtime Duplicate-Role Source Collapse

- Updated `app/db/rbac.py` so `resolve_tool_mode()` no longer emits one source per assigned role row for canonical-ish legacy duplicates; it now groups assigned role grants by logical canonical name before source emission.
- Kept the collapse bounded to canonical-ish names only: duplicate grants for the same logical canonical role are conservatively combined with the existing mode ordering, while unknown noncanonical legacy roles still retain per-row behavior and safe ordering.
- Emitted a stable canonical runtime source label like `role:org_admin` for grouped canonical-ish duplicates so effective-permission traces no longer leak raw legacy names such as `role: Org_Admin `.
- Added a failing-first regression in `tests/db/test_rbac_repository.py` that seeds two semantically duplicate legacy `org_admin` rows, assigns both, grants conflicting modes, and proves effective resolution returns one conservatively combined logical source.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py -q` (`6 passed` after fix; failing-first repro was `1 failed, 5 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q` (`10 passed`)

### 2026-04-22 Phase 4 Slice P4.1c RBAC Canonical-Ish Legacy Duplicate Collapse

- Updated `app/db/rbac.py` so canonical-name lookup now scans all semantically matching stored rows before trusting `role_keys`, deterministically chooses the oldest `(created_at, id)` survivor, and repairs the canonical key to that survivor.
- Added read-path presentation/collapse helpers so `list_roles()` returns at most one logical role per canonical normalized name while still leaving unknown legacy role names untouched; canonical-ish survivors are presented as canonical names like `org_admin` even if the stored row is `" Org_Admin "`.
- Kept strict canonical validation for new input and the existing lazy canonicalization-on-touch behavior in `create_role()`, so a canonical create now updates the deterministic survivor instead of whichever duplicate `role_keys` happened to reference.
- Expanded `tests/db/test_rbac_repository.py` with a failing-first regression that seeds two semantically duplicate legacy rows directly into the store, including a stale canonical key pointing at the newer duplicate, and proves lookup/list/create collapse them to one logical `org_admin` role.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py -q` (`5 passed` after fix; failing-first repro was `1 failed, 4 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q` (`9 passed`)

### 2026-04-22 Phase 4 Slice P4.1b RBAC Legacy Role Backward-Compat Hardening

- Added `normalize_stored_org_role_name()` in `app/models/rbac.py` so stored/read-path normalization trims and lowercases without strict enum rejection, while `normalize_org_role_name()` still enforces canonical-only validation for new requested role names.
- Updated `org_role_sort_key()` to order canonical names first but fall back safely for unknown legacy stored names instead of raising during role listing, assignment listing, or effective-permission resolution.
- Updated `app/db/rbac.py` to scan existing stored roles by loose normalized name when canonical lookup misses, repair the canonical role-key index on match, and lazily canonicalize a matched legacy role name when `create_role()` touches it so canonical input dedupes instead of creating a semantic duplicate.
- Added focused regression coverage in `tests/db/test_rbac_repository.py` proving legacy unknown stored names no longer crash read/effective paths and canonical input dedupes against legacy canonical-ish stored names like `" Org_Admin "`.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py -q` (`5 passed` after fix; failing-first repro was `2 failed, 3 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_rbac_repository.py tests/api/test_rbac.py -q` (`9 passed`)

### 2026-04-22 Phase 3 Slice P3.5 Hermes Tool Skill-Surface Gating

- Updated `app/services/hermes_tools_service.py` so `list_tools(agent_revision_id=...)` resolves the revision's bound skills, intersects their `required_tools` with `POLICY_BY_COMMAND`, and only narrows the exposed Hermes command surface when that intersection is non-empty.
- Kept backward compatibility open by falling back to the full Hermes command surface when a revision has no skills or its resolved skills only declare empty/non-command `required_tools` such as legacy metadata like `lookup_title`.
- Added invoke-time gating in `HermesToolsService.invoke_tool()` so command-backed tools outside the resolved skill surface raise `ToolPermissionError` and therefore stay API-level `403`s without replacing existing permission/RBAC/capability checks for still-visible tools.
- Added focused API regressions in `tests/api/test_hermes_tools.py` covering surface intersection, non-command fallback, and out-of-surface invocation rejection.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py -q` (`12 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_permissions.py tests/api/test_rbac.py tests/services/test_hermes_tools_service.py -q` (`19 passed`)

### 2026-04-22 Phase 3 Slice P3.4c Agent-Backed Replay Dispatch Continuity

- Added `HostAdapterDispatchesRepository.get_by_run_id()` so replay resolution can reuse the existing in-memory/hydrated host-adapter dispatch seam to recover the parent run's `agent_revision_id` without adding new persistence wiring.
- Updated `app/services/replay_service.py` so safe-autonomous replays derive `agent_revision_id` from the parent run's adapter dispatch, create child runs through `run_service.create_run(..., agent_revision_id=...)`, and only append replay events after successful child-run or approval creation to avoid partial replay state on failure.
- Updated `app/api/replays.py` to translate replay-time dispatchability failures into clean `422` responses instead of surfacing a `500`.
- Added API regression coverage in `tests/api/test_replays.py` proving agent-backed replays create a second adapter dispatch correlated to the child run id, non-agent replay behavior stays intact, and archived revisions fail cleanly without bogus child runs or dispatches.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_replays.py -q` (`4 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_replays.py tests/api/test_hermes_tools.py tests/api/test_commands.py -q` (`19 passed`)

### 2026-04-22 Phase 3 Slice P3.4b Agent-Backed Command Idempotency Restore

- Added `CommandsRepository.get_by_idempotency_key()` for both in-memory and existing Supabase-backed command lookups without changing persistence ownership or schema wiring.
- Updated `CommandService.create_command()` so agent-backed safe-autonomous retries short-circuit to the original persisted command/run before dispatchability validation, while brand-new invalid/draft/archived/disabled requests still fail closed before any queue records are created.
- Added QC regression coverage in `tests/api/test_hermes_tools.py` and `tests/api/test_commands.py` proving archived-revision retries with the same idempotency key return the original deduped command/run and do not create a second adapter dispatch.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_commands.py tests/services/test_agent_execution_service.py tests/services/test_hermes_tools_service.py -q` (`23 passed`)
  - `./.venv/bin/python -m pytest tests/db/test_commands_repository.py tests/db/test_control_plane_supabase_adapters.py -q` (`8 passed`)

### 2026-04-22 Phase 3 Slice P3.4a Hermes Tool Agent-Dispatch Runtime Path

- Extended `app/models/commands.py`, `app/services/hermes_tools_service.py`, `app/services/command_service.py`, and `app/services/run_service.py` so Hermes tool invocations now carry optional `agent_revision_id` into the safe-autonomous runtime path.
- Safe-autonomous agent-backed execution now pre-validates dispatchability through `agent_execution_service` before command/run persistence, rejecting missing, draft, archived, and disabled-adapter revisions without leaving queued command/run leftovers; non-agent safe-autonomous behavior and approval-required behavior remain unchanged.
- `agent_execution_service` still dispatches published revisions through the host-adapter seam, keeps `run.id` as the adapter correlation/external reference, and now treats disabled adapters as non-dispatchable instead of returning a queued-looking no-op.
- Added focused API/service coverage in `tests/api/test_hermes_tools.py`, `tests/api/test_commands.py`, and `tests/services/test_agent_execution_service.py` for the fail-closed QC repros while preserving the existing happy-path adapter dispatch and non-agent no-dispatch behavior.
- Verified with:
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_commands.py tests/services/test_agent_execution_service.py -q` (`18 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_hermes_tools.py tests/api/test_commands.py tests/services/test_agent_execution_service.py tests/api/test_agents.py -q` (`31 passed`)

### 2026-04-22 Phase 3 Slice P3.3 Host-Adapter Contract Hardening

- Hardened `app/models/host_adapters.py`, `app/host_adapters/base.py`, `app/host_adapters/registry.py`, `app/host_adapters/trigger_dev.py`, `app/host_adapters/codex.py`, and `app/host_adapters/anthropic.py` so the adapter seam now explicitly models dispatch, status correlation, artifact reporting, cancellation, and disabled behavior.
- Added adapter read-model metadata for later runtime/UI work, including `display_name`, `adapter_details_label`, `capabilities`, and `disabled_reason`, while keeping Trigger-specific information framed as adapter details rather than product identity.
- Kept Codex and Anthropic registered but disabled, unified their disabled/no-op behavior through the shared base contract, and added duplicate-kind protection in the host registry.
- Expanded focused coverage in `tests/host_adapters/test_host_registry.py`, `tests/host_adapters/test_trigger_dev_adapter.py`, and `tests/host_adapters/test_disabled_host_adapters.py` for adapter descriptions, correlation records, artifact reporting, cancellation handling, and disabled-adapter contract behavior.
- Verified with:
  - `./.venv/bin/python -m pytest tests/host_adapters/test_host_registry.py tests/host_adapters/test_trigger_dev_adapter.py tests/host_adapters/test_disabled_host_adapters.py -q` (`8 passed`)
  - `./.venv/bin/python -m pytest -q` (`392 passed`)

### 2026-04-22 Phase 3 Slice P3.2 Skill Registry Contract Hardening

- Hardened `app/models/skills.py`, `app/db/skills.py`, `app/services/skill_registry_service.py`, and `app/api/skills.py` so skills now carry explicit `permission_requirements` alongside normalized `name`, `description`, `required_tools`, and input/output contract metadata.
- Added defensive-copy behavior in the skills repository so nested contract metadata and tool/permission lists cannot be mutated through returned records.
- Kept agent revisions bound to `skill_ids` only and tightened missing-skill error reporting to return a clean deduplicated `Unknown skill ids: ...` failure.
- Added focused repository/API coverage in `tests/db/test_skills_repository.py` and `tests/api/test_skills.py`, then verified `tests/api/test_agents.py` still passes for skill-id binding behavior.
- Verified with:
  - `./.venv/bin/python -m pytest tests/db/test_skills_repository.py tests/api/test_skills.py -q` (`6 passed`)
  - `./.venv/bin/python -m pytest tests/api/test_agents.py -q` (`13 passed`)
  - `./.venv/bin/python -m pytest -q` (`388 passed`)

### 2026-04-22 Phase 2 Lane C Org Directory Tenant Isolation

- Hardened `app/api/organizations.py`, `app/api/memberships.py`, `app/services/organization_service.py`, and `app/services/access_service.py` so org directory reads/writes now resolve against the header-derived actor org instead of global memory state.
- `GET /organizations` now only returns the caller's org record, foreign org detail reads return `404`, and mismatched org writes fail with `422`.
- `GET /memberships` now scopes to the caller org by default, rejects cross-org `org_id` query overrides with `422`, and blocks cross-org membership detail/write access cleanly.
- Added focused API coverage in `tests/api/test_organizations.py` and `tests/api/test_memberships.py`, including `X-Ares-Org-Id` actor-header regressions for the QC repros.
- Verified with targeted coverage only: `uv run pytest tests/api/test_organizations.py tests/api/test_memberships.py -q` (`5 passed`).

### 2026-04-22 Phase 2 Lane B Org-Scoped API Hardening

- Hardened `app/api/permissions.py`, `app/api/rbac.py`, `app/services/permission_service.py`, and `app/services/rbac_service.py` so the existing header-based actor org now gates permission/RBAC reads and writes.
- Tightened cross-org failure behavior for permission/RBAC paths and `POST /sessions` without touching Supabase wiring, migrations, or Mission Control surfaces.
- Added tenant-isolation API coverage for agents, sessions, permissions, and RBAC proving the same `business_id` / `environment` can exist in multiple orgs without leakage.
- Verified the lane with targeted pytest coverage only: `tests/api/test_permissions.py tests/api/test_rbac.py tests/api/test_agents.py tests/api/test_sessions.py`.

### 2026-04-22 In-Memory Org Directory Slice

- Added first-class in-memory `organizations` and `memberships` models, repositories, and services without touching Supabase wiring.
- Seeded the default internal org plus an internal runtime membership inside the in-memory control-plane store so existing `org_internal` defaults resolve cleanly.
- Mounted authenticated `organizations` and `memberships` API routes and added focused repository/API coverage for the new slice.

### 2026-04-21 Mission Control + Enterprise Backlog Branch Reset

- Created `feature/mission-control-enterprise-backlog` from current `main` as the new combined-scope branch for Mission Control orchestration + enterprise platform backlog work.
- Added `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md` as the canonical execution plan for that branch.
- Corrected the mistaken deprecation on `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`; it is now a live source plan again.
- Repointed `TODO.md`, `CONTEXT.md`, and `memory.md` for the combined branch so the older loose-ends handoff no longer drives current scope there.

### 2026-04-20 Shared Control-Plane Runtime Supabase Pass

- Added `supabase/migrations/202604200001_shared_control_plane_runtime.sql` for the remaining text-id control-plane runtime entities:
  - agents / revisions
  - sessions / memory summaries
  - turns / turn events
  - permissions / RBAC / secrets
  - audit / usage / outcomes
  - agent assets / Mission Control threads / skills / host adapter dispatches
- Added `app/db/control_plane_store_supabase.py` and upgraded `SupabaseControlPlaneClient.transaction()` to hydrate and flush the remaining control-plane store sections through Supabase instead of raising `NotImplementedError`
- This preserves the existing repository/service contracts for the managed-agent and Mission Control surfaces while making `control_plane_backend=supabase` actually usable across the broader runtime
- Added focused persistence coverage in `tests/db/test_supabase_control_plane_client.py`
- Verified repo state after the pass with:
  - `244 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - local Supabase `db reset --local` passing on April 20, 2026

### 2026-04-20 Control-Plane Supabase Wiring Pass

- Added a shared `app/db/control_plane_supabase.py` adapter layer for the core control-plane tables already present in `202604130001_hermes_control_plane_core.sql`
- Wired explicit Supabase-backed repository paths for:
  - `commands`
  - `approvals`
  - `runs`
  - `events`
  - `artifacts`
- Fixed the persistence bug where memory-mode object mutation masked missing writes in Supabase mode:
  - command ingestion now persists approval/run status transitions explicitly
  - run lifecycle callbacks now persist run status updates before recording events
  - run creation now records the initial `run_created` event through the repository seam instead of only mutating the in-memory object
- Added focused adapter coverage in `tests/db/test_control_plane_supabase_adapters.py`
- Verified repo state after the pass with:
  - `242 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - Mission Control frontend `vitest` passing locally

### 2026-04-20 Loose-Ends QC Blocker Fixes

- Fixed inbound SMS stop/pause mutation scoping:
  - `InboundSmsService` now passes the resolved lead identity into sequence mutation calls
  - `_SequenceReplyAdapter` now resolves active enrollments with scoped `business_id + environment + contact_id` when available instead of relying on global phone lookup
  - ambiguous/unresolved replies still create manual-review tasks and receipts, but do not mutate sequence state
- Fixed provider-thread resolution safety:
  - `_resolve_inbound_lead()` now uses provider-thread matching only when tenant metadata is present
  - unscoped provider-thread fallback is skipped, so duplicate thread IDs without tenant metadata fall through to manual review / phone resolution only
  - in-memory `ConversationsRepository` no longer keys rows by `provider_thread_id`, so duplicate external thread IDs can coexist across tenants
- Added regression coverage for:
  - shared-phone stop replies only stopping the resolved tenant's sequence
  - duplicate provider-thread IDs resolving correctly with tenant metadata
  - unscoped provider-thread metadata skipping the global thread matcher
- Verified with `uv run pytest tests/services/test_inbound_sms_service.py tests/api/test_marketing_webhooks.py -q` (`16 passed`)

### 2026-04-20 Ralph Story-06 Verification

- Completed branch-level rollout gates for the loose-ends MVP in memory mode:
  - backend: `uv run pytest -q` (`257 passed`)
  - Mission Control: `typecheck`, `vitest --run` (`14 passed`), `build`
  - Trigger: `npm --prefix trigger run typecheck`
- Executed fixture-backed smoke flows:
  - lease-option submit -> booking webhook -> sequence guard (`booked` -> `stopped`)
  - probate intake -> outbound enqueue -> Instantly webhook ingest
- Verified runtime startup/health with Supabase env vars unset and all backends forced to memory (`MEMORY_STARTUP=PASS`).

### 2026-04-20 Ralph Story-05 Verification

- Added RED/GREEN coverage for thin opportunity seam progression:
  - direct opportunity forward-stage transition (`qualified_opportunity -> offer_path_selected`)
  - Mission Control operator task completion path that advances lease-option opportunities when follow-up outcome marks the contact ready
- Added Mission Control service opportunity sync from thread context for lease-option contacts:
  - uses booking status and follow-up outcome to decide whether to open/advance opportunity
  - resolves marketing contact from thread context `lead_id` (contact id) or phone fallback
  - advances to `offer_path_selected` when operator marks outcome ready
- Verified story-05 gates with:
  - `uv run pytest -q` (`257 passed`)
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run` (`14 passed`)
  - `npm --prefix apps/mission-control run build`

### 2026-04-20 Ralph Story-04 Verification

- Added explicit lane-separated Mission Control dashboard read models:
  - `outbound_probate_summary`
  - `inbound_lease_option_summary`
  - `opportunity_pipeline_summary` (lane+stage summaries)
- Kept additive compatibility by retaining existing dashboard totals while exposing lane-specific aggregates for Mission Control workspace badges/context.
- Updated Mission Control frontend mapping and fixtures so opportunity stages preserve `source_lane` instead of flattening by stage.
- Updated Pipeline board rendering so stage cards remain lane-labeled and do not collapse probate vs lease-option rows.
- Verified story-04 gates with:
  - `uv run pytest -q` (`255 passed`)
  - `npm --prefix apps/mission-control run typecheck`
  - `npm --prefix apps/mission-control run test -- --run` (`14 passed`)
  - `npm --prefix apps/mission-control run build`

### 2026-04-20 Ralph Story-03 Verification

- Hardened the lease-option inbound lane in memory mode with:
  - sequence guard state derived from latest enrollment status (active/paused/completed/stopped) for pending leads
  - booking-confirmation timeline logging into `messages` for SMS and email channels when configured
  - inbound SMS resolution order: provider thread metadata first, then tenant-scoped phone matching
  - explicit manual-review task creation when inbound SMS lead resolution is ambiguous or unmatched
- Added focused regression coverage for:
  - paused sequence guard behavior
  - booking confirmation message timeline writes
  - thread-first inbound SMS resolution
  - ambiguity task creation for duplicate phone matches
- Verified lease-option and full backend gates with:
  - `uv run pytest tests/services/test_booking_service.py tests/api/test_marketing_webhooks.py -q` (`14 passed`)
  - `uv run pytest tests/api/test_marketing_leads.py tests/api/test_marketing_webhooks.py tests/api/test_marketing_runtime.py tests/api/test_marketing_sequence.py tests/domains/marketing/test_marketing_flow.py tests/services/test_booking_service.py -q` (`33 passed`)
  - `uv run pytest -q` (`255 passed`)

### 2026-04-20 Ralph Story-02 Verification

- Verified the probate outbound write path acceptance gate in memory-backed mode for:
  - `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
- Confirmed replay-safe webhook handling and receipt-first processing remain covered by existing API/service tests
- Verified branch health with `uv run pytest -q` (`251 passed`) and `npm --prefix trigger run typecheck`
- Updated Ralph board state so `story-02-build-probate-outbound-write-path` is marked `done` / `passes: true`

### 2026-04-20 Loose-Ends Scope Repoint

- Repointed the loose-ends branch back to the probate outbound + lease-option inbound MVP implementation plan
- Kept the 2026-04-15 enterprise-agent-platform plan in the repo but marked it deprecated
- Restored `TODO.md`, `CONTEXT.md`, and `memory.md` to the lead-machine / two-lane MVP scope

### 2026-04-21 Phase5 Guarded Autonomous Operator Wiring

- Added `app/services/ares_autonomous_operator_service.py` to wire the guarded operator loop across:
  - versioned Ares agent registry initialization (`ares_guarded_operator` revision `v1`)
  - playbook execution for approved objectives
  - deterministic high-risk policy gates (outreach/contract/spending/market-expansion require approval)
  - durable memory journaling and evaluation-loop metric recording
- Added `POST /ares/operator/run` in `app/api/ares.py` to execute approved objective runs and persist latest operator snapshot per `(business_id, environment)` in control-plane scope state.
- Extended Mission Control autonomy visibility contracts and service wiring to surface `autonomous_operator` summary with decisions, exceptions, policy checks, audit log, adaptation summary, and escalation state.
- Updated `app/main.py` startup wiring to initialize the guarded autonomous operator surface on app creation.
- Extended tests:
  - `tests/api/test_mission_control_phase3.py` with guarded operator visibility coverage
  - `tests/test_package_layout.py` with `/ares/operator/run` route registration coverage
- Verified with `uv run pytest tests/api/test_mission_control_phase3.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase4 Execution + Mission Control Workflow Integration

- Updated `POST /ares/execution/run` in `app/api/ares.py` to integrate the workflow playbook runner on each bounded execution run.
- Added explicit high-risk policy checks for send/contract/disposition actions on each run, with hard-approval-required outcomes surfaced in runtime output and execution snapshots.
- Added per-scope drift detection against the previous execution snapshot and persisted drift status/reason into execution review data.
- Added workflow evaluation output (`workflow_id`, exception count, surfaced exceptions, suggested next action) into execution review snapshots.
- Extended Mission Control execution review contracts in `app/models/mission_control.py` to include:
  - high-risk policy checks
  - workflow eval summary
  - drift detection summary
  - major decisions and major failures
- Extended `tests/api/test_mission_control_phase3.py` to cover:
  - hard-approval-required high-risk checks in autonomy visibility
  - workflow eval + major decision/failure surfacing
  - drift detection visibility across consecutive execution runs in the same scope
- Verified with `uv run pytest tests/api/test_mission_control_phase3.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase4 Playbook, State, and Eval Services

- Added `app/services/ares_playbook_service.py` as a deterministic workflow runner that can:
  - choose county/market slice
  - pull probate/tax signals via county adapters
  - enrich and score leads through existing matching logic
  - generate outreach drafts and follow-up approval tasks
  - monitor response events and set next-best-action
- Added `app/services/ares_state_service.py` for workflow state memory with per-step status/history plus retry and fallback handling.
- Added `app/services/ares_eval_service.py` to capture and surface workflow exceptions in explicit eval reports (no silent drops).
- Added service coverage:
  - `tests/services/test_ares_playbook_service.py`
  - `tests/services/test_ares_state_service.py`
  - `tests/services/test_ares_eval_service.py`
- Verified with `uv run pytest tests/services/test_ares_playbook_service.py tests/services/test_ares_state_service.py tests/services/test_ares_eval_service.py -q`.

### 2026-04-21 Phase4 Workflow Models and Contracts

- Added `app/domains/ares_workflows/models.py` with workflow contract models for:
  - county or market workflow scope (`AresWorkflowScope`)
  - per-step workflow state (`AresWorkflowStepState` + `AresWorkflowStepStatus`)
  - next-best-action and append-only workflow history (`AresWorkflowState` + `record_history`)
- Added workflow domain exports in `app/domains/ares_workflows/__init__.py`.
- Added workflow model contract tests in `tests/domains/ares_workflows/test_workflow_models.py`.
- Extended package export checks in `tests/test_package_layout.py` for `app.domains.ares_workflows`.
- Verified with `uv run pytest tests/domains/ares_workflows/test_workflow_models.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase3 Execution API + Mission Control Wiring

- Added `POST /ares/execution/run` in `app/api/ares.py` to launch bounded execution runs through `AresExecutionService` with explicit run scope (`market`, up to two counties, budget/retry/allowlist) and deterministic county payload adapters.
- Persisted the latest bounded execution snapshot per `(business_id, environment)` in the in-memory store as `ares_execution_runs_by_scope`.
- Extended Mission Control autonomy visibility to surface `execution_review` with bounded run state (`completed|completed_with_failures|interrupted`) plus execution result summary (lead/failure counts and ranked lead tier output).
- Updated phase-3 API tests in:
  - `tests/api/test_ares_runtime.py`
  - `tests/api/test_mission_control_phase3.py`
  - `tests/test_package_layout.py` (route registration for `/ares/execution/run`)
- Verified with `uv run pytest tests/api/test_ares_runtime.py tests/api/test_mission_control_phase3.py tests/test_package_layout.py -q`.

### 2026-04-21 Phase3 Bounded Execution Service

- Expanded `app/services/ares_execution_service.py` from guardrails-only authorization into a bounded execution pipeline that:
  - fetches county probate/tax payloads via deterministic county fetch adapters
  - normalizes record fields and dedupes overlap records per county/lane/address
  - enriches probate records from matching tax records when data is available
  - runs overlay matching with ranked lead outputs
  - generates lead briefs, outreach drafts, task suggestions, and follow-up work queue items
  - surfaces county fetch failures as explicit recoverable run output failures and supports run interruption via kill-switch
- Reworked `tests/services/test_ares_execution_service.py` to validate the bounded pipeline behavior plus existing execution guardrail enforcement.
- Verified with `uv run pytest tests/services/test_ares_execution_service.py -q`.

### 2026-04-21 Phase3 Execution Contracts and Guardrails

- Added bounded execution contract models in `app/domains/ares/models.py`:
  - `AresExecutionRunSpec` (narrow county-scoped run, action budget, retry limit, approved tool allowlist)
  - `AresExecutionActionSpec` (typed action authorization request contract)
  - `AresExecutionDecision` and `AresExecutionGuardrailResult` (deterministic guardrail decisions)
- Added `app/services/ares_execution_service.py` with guardrail enforcement for:
  - tool allowlist
  - retry-limit checks
  - run-level action budget exhaustion checks
  - policy-service delegated risky-call approvals
  - audit trail and kill-switch deny behavior
- Added `tests/services/test_ares_execution_service.py` for bounded-run model and guardrail contract coverage.
- Verified phase-3 guardrails with:
  - `uv run pytest tests/services/test_ares_policy_service.py tests/services/test_ares_execution_service.py -q`

### 2026-04-21 Phase2 Planner API + Mission Control Review Surface

- Added `POST /ares/plans` in `app/api/ares.py` to expose deterministic planner output and explanation for operator review.
- Persisted latest planner snapshot per `(business_id, environment)` in the in-memory control-plane store (`ares_plans_by_scope`).
- Extended Mission Control autonomy visibility with `planner_review` so the latest planner goal/explanation/plan is visible in one response.
- Added `tests/api/test_ares_plans.py` for planner request/response contract and Mission Control planner surfacing.
- Updated package-layout route assertions for `/ares/plans` and verified with:
  - `uv run pytest tests/api/test_ares_plans.py tests/test_package_layout.py -q`

### 2026-04-21 Phase2 Planner Service Logic

- Added `app/services/ares_planner_service.py` with deterministic planning logic to:
  - parse goal text into county slices and source lanes
  - choose planner checks for county scope, overlay match quality, and approval gate enforcement
  - generate concrete sequential planner steps with explicit side-effecting action approval requirements
  - produce operator-facing plan explanation text (`explain_plan`)
- Extended `AresPlannerPlan` in `app/domains/ares/models.py` with optional `counties` to capture county-slice planning scope
- Added `tests/services/test_ares_planner_service.py` covering:
  - probate+tax county-slice goal acceptance
  - lane/check selection
  - concrete steps plus side-effecting approval gate
  - operator explanation output
- Verified with `uv run pytest tests/services/test_ares_planner_service.py -q`

### 2026-04-21 Phase2 Planner Models and Contracts

- Added planner-domain contract models in `app/domains/ares/models.py`:
  - `AresPlannerCheck` for explicit checks
  - `AresPlannerStep` for step-by-step plans scoped to a source lane
  - `AresPlannerPlan` for goal, source lanes, checks, steps, and rationale
  - `AresPlannerActionType` with `read_only` and `side_effecting`
- Enforced side-effect approval in model validation: side-effecting steps must set `requires_approval=True`
- Exported planner models through `app/domains/ares/__init__.py` and package layout assertions
- Added planner model coverage in `tests/domains/ares_planning/test_planner_models.py`
- Verified with `uv run pytest tests/domains/ares_planning/test_planner_models.py tests/test_package_layout.py -q`

### 2026-04-21 Shared Mission Control Autonomy Visibility

- Added operator-facing autonomy visibility read model:
  - `GET /mission-control/autonomy-visibility`
  - `MissionControlAutonomyVisibilityResponse` with `current_phase`, `active_run`, pending approvals, failed steps, lead quality, confidence, and next action
- Added Mission Control phase-3 API coverage in `tests/api/test_mission_control_phase3.py` for the new autonomy visibility surface
- Verified with `uv run pytest tests/api/test_mission_control_phase3.py -q`

### 2026-04-21 Shared Evaluation Loop Foundation

- Added `app/services/ares_eval_loop_service.py` with durable JSON-backed evaluation-loop state and inspectable run entries
- Added typed evaluation primitives:
  - `AresEvalSample` for lead/response/conversion counts plus false positives, duplicate work, and operator corrections
  - `AresEvalMetrics` for lead quality, response quality, conversion quality, false-positive rate, duplicate-work rate, and operator-correction rate
  - `AresEvalResult` and `AresEvalLoopState` for stable persisted evaluation records
- Added `tests/services/test_ares_eval_loop_service.py` covering required metrics calculation, durable save/reload behavior, and stable metrics contract keys/zero-denominator behavior
- Verified with `uv run pytest tests/services/test_ares_eval_loop_service.py -q`

### 2026-04-21 Ares Shared Agent Registry Foundation

- Added versioned Ares agent registry primitives:
  - `app/domains/ares/agent_registry.py` with `AresAgentRevisionSpec` and `AresVersionedAgentRecord`
  - fields lock `name`, `purpose`, `revisions`, `allowed_tools`, `risk_policy`, `output_contract`, and `active_revision`
- Added `app/services/ares_agent_registry_service.py` to register revisions, track active revision, and export/import model snapshots
- Added round-trip coverage:
  - `tests/domains/ares/test_agent_registry_models.py`
  - `tests/services/test_ares_agent_registry_service.py`

### 2026-04-21 Ares Master Scope Docs + Memory Handoff

- Updated repo-facing handoff docs to point at the merged phased implementation plan as the execution source of truth:
  - `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md`
- Kept the master-scope PRD as the overnight loop handoff artifact:
  - `docs/superpowers/plans/2026-04-21-ares-crm-master-scope-prd.json`
- Restated Phase 1 hard guardrails in docs/memory surfaces:
  - counties remain Harris, Tarrant, Montgomery, Dallas, Travis
  - probate is primary and tax delinquency is overlay
  - outreach drafts remain pending human approval before send

### 2026-04-21 Ares Phase1 API Route

- Added `app/api/ares.py` with `POST /ares/run` to execute the phase-1 Ares runtime path:
  - county-filtered probate/tax intake
  - probate-first ranking with tax overlay via `AresMatchingService`
  - optional lead briefs and outreach drafts via `AresCopyService`
- Wired the new route in `app/main.py` so it is mounted in the protected FastAPI app
- Added `tests/api/test_ares_runtime.py` and updated package-layout coverage for route registration
- Verified with `uv run pytest tests/api/test_ares_runtime.py tests/test_package_layout.py -q`

### 2026-04-21 Ares Phase1 Matching Overlay Tiering

- Added `app/services/ares_service.py` with `AresMatchingService` and deterministic tiering:
  - probate lane is primary
  - verified tax delinquency is applied as an overlay on probate records by county + normalized property address
  - probate+verified-tax overlaps rank highest over probate-only
  - tax-only output is allowed only for estate-of records and only when no probate records are present
- Added `tests/services/test_ares_service.py` covering probate-first behavior, overlay matching, highest-rank overlap, county-aware matching, and estate-only tax-only constraints
- Verified with `uv run pytest tests/services/test_ares_service.py -q`

### 2026-04-16 Live Supabase Smoke + Adapter Hardening

- Repaired remote Supabase migration history on project `awmsrjeawcxndfnggoxw` and applied:
  - `202604160001_lead_machine_runtime.sql`
  - `202604160002_runtime_opportunities.sql`
- Corrected the live lease-option booking schema to allow `booked` events and verified the lane against remote Supabase:
  - `POST /marketing/leads` -> `201`
  - `POST /marketing/internal/non-booker-check` -> `200`
  - `POST /marketing/webhooks/calcom` -> `200`
  - remote evidence in `contacts`, `booking_events`, `sequence_enrollments`, and `provider_webhooks`
- Verified the probate outbound lane against remote Supabase with a stubbed Instantly transport:
  - `POST /lead-machine/probate/intake` -> `201`
  - `POST /lead-machine/outbound/enqueue` -> `200`
  - `POST /lead-machine/webhooks/instantly` -> `200`
  - remote evidence in `probate_leads`, `leads`, `automation_runs`, `campaign_memberships`, `provider_webhooks`, `lead_events`, `suppressions`, and `opportunities`
- Fixed several Supabase adapter seams uncovered by the live smoke pass:
  - lead-machine migration composite-tenant uniqueness ordering
  - lease-option booking event constraint mismatch (`booked` vs `created`)
  - Supabase rehydration for `probate_leads`, `leads`, `campaign_memberships`, `provider_webhooks`, `lead_events`, and `suppressions`
  - `automation_runs` Supabase insert excluding runtime-only `deduped`
  - campaign active-tenant guard accepting slug requests for numeric Supabase-backed campaigns
  - webhook lead resolution preferring direct email matches so replies attach to the routed probate lead
- Verified repo state after the fixes with `177 passed` backend tests via `./.venv/bin/python -m pytest -q`

### 2026-04-16 MVP Runtime Execution Pass

- Finished the probate outbound write path with:
  - typed `POST /lead-machine/probate/intake`
  - `POST /lead-machine/outbound/enqueue`
  - `POST /lead-machine/webhooks/instantly`
- Added `ProbateLeadsRepository` plus canonical `probate_leads` persistence in the intake flow
- Extended probate records to preserve `tax_delinquent`, `estate_of`, and `pain_stack`
- Tightened lead-machine API validation so malformed intake rows and malformed webhook payloads fail with `422` instead of leaking through as `500` / false-positive `200`
- Added the thin opportunity seam in live runtime paths:
  - probate positive reply / interested events create or update probate opportunities
  - first-time booked lease-option contacts create or update lease-option opportunities
- Fixed opportunity identity so records dedupe by `source_lane + identity`, preventing probate and lease-option rows from collapsing together
- Added additive Mission Control surfaces:
  - backend `GET /mission-control/lead-machine`
  - frontend workspaces for `Lead Machine`, `Marketing`, and `Pipeline`
- Verified the repo state with:
  - `168 passed` backend tests via `./.venv/bin/python -m pytest -q`
  - Mission Control `typecheck`, `vitest --run`, and `vite build`
  - Trigger `typecheck`

### 2026-04-16 Mission Control Lane Separation Backend Acceptance

- Added backend Mission Control coverage proving the operator dashboard keeps lease-option marketing counts, additive probate lead-machine counts, and persisted opportunity pipeline summaries separate
- Added an additive `lead_machine_summary` dashboard read model for probate outbound counts without changing the existing marketing inbox/tasks surfaces
- Tightened opportunity stage summaries so they are grouped by both `source_lane` and `stage`, preventing probate and lease-option pipeline rows from collapsing together

### 2026-04-16 Opportunity Creation Wiring Pass

- Wired `OpportunityService` into the live probate webhook path so positive reply and interested events create or update a probate opportunity record
- Wired `OpportunityService` into the live lease-option booking path so first-time booked contacts create or update a lease-option inbound opportunity record
- Added focused service tests covering the probate opportunity trigger and the lease-option booked-contact opportunity trigger

### 2026-04-16 Combined MVP Implementation Plan

- Added `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
- Locked tonight's MVP as a two-lane cut:
  - probate outbound via Instantly cold email
  - lease-option inbound via the existing marketing flow
- Decided to reuse the existing lease-option marketing slice in this branch and bring the newer probate / lead-machine slice forward from `origin/main`
- Decided to wire Supabase as the canonical backend for both live MVP lanes instead of deferring live persistence again
- Chose a shared-runtime split:
  - lease-option keeps its existing marketing objects
  - probate gets lane-specific lead-machine tables
  - both lanes share provider webhook receipts, tasks, Mission Control, and a thin `opportunities` seam

### 2026-04-16 Real Estate Runtime Thesis

- Added `docs/superpowers/specs/2026-04-16-ares-real-estate-runtime-thesis-design.md`
- Locked the product direction: Ares is the reusable runtime, not the main agent
- Chose the long-term domain map: data gathering, prospecting, acquisitions, transaction coordination, title, and dispo
- Chose the architecture split:
  - source lanes describe where an opportunity came from
  - strategy lanes describe how the opportunity may be solved or monetized
  - operational stages describe where the record is in the business process
- Locked the current MVP shape:
  - source lane = probate
  - outbound method = cold email
  - downstream skeleton = thin contract-to-close placeholders for title, TC, and dispo
- Confirmed that tax distress and estate signals should become composite pain-stack inputs, especially `estate_of + tax_delinquent`

### 2026-04-14 Lease-Option Marketing Wiring Pass

- Replaced the landing-page `n8n` handoff with Hermes lead-ingress payloads while keeping the old `n8n` helper type-compatible for legacy tests
- Wired `MarketingLeadService` to configured `TextGrid`, `Resend`, `Cal.com` booking URLs, and Trigger HTTP scheduling instead of the earlier no-op defaults
- Wired booking confirmations, manual-call task persistence, and sequence-step outbound dispatch onto the current in-memory marketing repositories
- Added exact-config support for local env names already present on Martin's machine, including `Cal_API_key` and Trigger settings
- Added webhook-signature enforcement seams for `Cal.com` and `TextGrid` using request details from the FastAPI routes
- Verified current repo state with `95` backend tests passing, Mission Control tests/build passing, Trigger typecheck passing, and landing-page tests/build passing
- Added a marketing-only Supabase adapter layer and verified a live smoke insert into remote `public.contacts` for `limitless/dev`
- Applied the core and lease-option marketing migrations to Supabase project `awmsrjeawcxndfnggoxw` and seeded `public.businesses` with `limitless/dev`
- Kept the repo honest about the remaining MVP risks: inbound SMS matching is still phone-only and sequence guard state is still derived too simplistically for a multi-tenant or more advanced sequence rollout

### 2026-04-14 Lease-Option Marketing MVP Design

- Added `docs/superpowers/specs/2026-04-14-lease-option-marketing-mvp-design.md` as the live marketing MVP design
- Locked the first live scope to lease-option sellers with `45+ DOM` messaging
- Chose `Cal.com` for booking, `TextGrid` for SMS, and `Resend` for transactional email
- Chose the lead-state rule: submit creates `pending`, booking flips to `booked`, and only non-bookers after 5 minutes enter the 10-day intensive
- Chose Hermes to replace the current landing-page `n8n` handoff so booking state, sequence state, inbound replies, and manual-call tasks live in one control plane

### 2026-04-13 Mission Control Finish Plan

- Added `docs/superpowers/plans/2026-04-13-mission-control-finish-plan.md` to separate safe branch completion from later Supabase persistence work
- Captured the recommended rollout order: finish backend/frontend Mission Control contract first, then do additive Supabase migrations in a separate gated pass
- Noted that the branch can be finished without immediate schema changes because the current blocking work is contract alignment, not persistence

### 2026-04-13 Mission Control Docs Sync

- Updated README, CONTEXT, memory, and Mission Control planning/spec docs to reflect the phase-6 landed read models and native shell
- Corrected stale repo-root references in the orchestration plan
- Kept the current phase focus on docs/release-gate cleanup while Supabase persistence remains deferred

### 2026-04-13 Mission Control Frontend Shell

- Added `apps/mission-control/` as a minimal React/TypeScript Mission Control app scaffold with a dense native shell, dashboard, inbox, approvals, runs, agents, and settings/assets surfaces
- Added a typed Mission Control API client, tiny query cache helper, and local fixtures so the UI remains buildable and testable without live Supabase or live backend coupling
- Added Vite/Vitest/TypeScript setup plus targeted UI tests covering shell navigation/search rendering and dashboard count rendering from fixture data

### 2026-04-12 Repo Bootstrap

- Created the clean `Hermes Central Command` repo path
- Confirmed a fresh Supabase project is reachable
- Confirmed migration dry-run access works against the new project
- Ported WAT and memory/context operating conventions into the new repo
- Added Trigger.dev bootstrap files and verified `trigger:dev` reaches a ready local worker
- Added `CODEX.md` with subagent orchestration and cleanup rules

### 2026-04-13 Managed-Agent Scaffold Phase 5

- Added in-memory managed-agent scaffolding for versioned agents, revisions, sessions, tool permissions, outcomes, and connect-later operational assets
- Added FastAPI routes for agents, sessions, permissions, outcomes, and agent assets
- Updated Hermes tools to respect explicit `always_allow`, `always_ask`, and `forbidden` permission policies without adding live Supabase wiring
- Added a scaffold-only Supabase migration placeholder for the deferred managed-agent schema seam
- Added targeted API and package-layout tests covering the new phase-5 surface

### 2026-04-13 Mission Control Read Models

- Added scaffold-first Mission Control read models for dashboard, inbox, and run lineage backed only by the in-memory control-plane store
- Added protected FastAPI routes for `/mission-control/dashboard`, `/mission-control/inbox`, and `/mission-control/runs`
- Added targeted API and package-layout tests covering dashboard counts, seeded inbox threads, and replay lineage with `parent_run_id`

### 2026-04-13 Control Plane Foundation

- Added typed command, approval, run, replay, and site-event runtime models
- Added FastAPI routes for commands, approvals, runs, replays, Hermes tools, and site events
- Added in-memory services to support idempotent command ingestion and replay safety
- Added Trigger.dev marketing worker chain scaffold in `trigger/`
- Added landing-page site-event forwarding plus runtime ingestion tests

### 2026-04-13 Mission Control Plan Rewrite

- Rewrote the Mission Control orchestration plan under `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- Made Hermes portability explicit: platform-agnostic core, installable anywhere the runtime stack can run
- Added feature-fit, anti-lock-in, and anti-duplication language so borrowed cloud-computer patterns stay adapter-friendly and Trigger.dev remains the durable execution backbone

### 2026-04-19 Ares North Star

- Framed Ares in repo-facing docs as the self-hosted operating system for distressed real-estate lead management; the operator UI is a visibility layer, not the core product.

### 2026-04-21 Ares Phase1 Models Contracts

- Added a new `app.domains.ares` domain module with explicit exports for `AresCounty`, `AresSourceLane`, `AresRunRequest`, and `AresLeadRecord`
- Locked county enum ordering to Harris, Tarrant, Montgomery, Dallas, Travis
- Locked run-request defaults with `include_briefs=True` and `include_drafts=True`, and county-string coercion into `AresCounty`
- Added explicit `estate_of` inference that marks records when owner names contain `estate of` or when the source lane is tax delinquency
- Added domain tests and package layout coverage for the new Ares domain module and verified the story command passes

### 2026-04-21 Ares Phase1 Briefs Drafts

- Added `app/services/ares_copy_service.py` with deterministic generation for operator-facing lead briefs and outreach drafts from ranked Ares opportunities
- Locked draft gating in code with `approval_status=\"pending_human_approval\"` and `auto_send=False` so drafts stay human-review-only
- Preserved rationale, county, source lane, and rank in both brief and draft outputs
- Added `tests/services/test_ares_copy_service.py` covering concise brief generation and pending-approval draft generation paths

### 2026-04-21 Shared Durable Memory Foundation

- Added `app/services/ares_memory_service.py` with JSON-backed durable memory state for market preferences, county defaults, lead history, outreach history, operator decisions, outcomes, and exceptions
- Added `tests/services/test_ares_memory_service.py` covering empty-load defaults and save/reload persistence across service instances
- Verified `uv run pytest tests/services/test_ares_memory_service.py -q` passes

### 2026-04-21 Shared Deterministic Tool Policy Foundation

- Added `app/services/ares_policy_service.py` with explicit tool allowlists, typed input/output contract validation, magical side-effect blocking, risky-call hard approval gating, audit entries, and kill-switch enforcement
- Added `tests/services/test_ares_policy_service.py` covering allowlist denial, typed contracts, magical side-effect blocking, hard-approval requirements, and audit/kill-switch behavior
- Verified `uv run pytest tests/services/test_ares_policy_service.py -q` passes
