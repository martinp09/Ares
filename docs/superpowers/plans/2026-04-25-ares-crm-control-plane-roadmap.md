# Ares CRM Control Plane Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans before implementation. This roadmap is a product/specification plan, not an execution checklist with code steps.

**Goal:** Turn Ares Mission Control into a CRM-backed business control plane for real-estate operations and agent supervision.

**Architecture:** Keep Ares as the deterministic runtime and source of truth. Extend Mission Control into a CRM shell, then add canonical CRM graph tables, pipeline configuration, activity/timeline models, task/reminder associations, and scoped agent workbench actions.

**Tech Stack:** FastAPI, Pydantic, Supabase/Postgres, React, Tailwind CSS, Trigger.dev, provider adapters.

---

## Phase 0: Spec Approval And Baseline Lock

**Outcome:** The branch has an approved design, known current baseline, and no accidental production changes.

**Files:**
- `CONTEXT.md`
- `memory.md`
- `docs/superpowers/specs/2026-04-25-ares-crm-control-plane-design.md`
- `docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md`
- `docs/mission-control-wiki/concepts/ares-crm-control-plane.md`

**Checks:**
- Confirm branch is `feature/ares-crm-control-plane-planning`.
- Review open decisions in the spec.
- Run `git diff --check`.

**Exit Gate:**
- User approves the spec direction or marks changes before implementation.

## Phase 1: CRM Shell From Existing State

**Outcome:** Mission Control feels like a working CRM shell without new schema risk.

**Backend:**
- Extend `/mission-control/dashboard` read model to include stale opportunities, opportunities without next task, due reminders placeholder, provider failures, and active agent run cards.
- Extend `/mission-control/lead-machine`, `/mission-control/tasks`, `/mission-control/runs`, and `/mission-control/inbox` into reusable CRM read-model inputs.
- Add tests around read-model aggregation from current repositories.

**Frontend:**
- Upgrade `DashboardPage`, `PipelinePage`, `TasksPage`, and `InboxPage`.
- Add `OpportunitiesPage` if the existing `PipelinePage` is too narrow.
- Keep styling aligned with `docs/design/ares-dashboard-theme-2026-04-25.md`.

**Verification:**
- `uv run pytest tests/api/test_mission_control.py tests/services/test_mission_control_service.py -q`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`

## Phase 2: Configurable Pipelines And Stage History

**Outcome:** Opportunities are no longer constrained to hard-coded enum stages only.

**Backend:**
- Add migrations for `crm_pipelines`, `crm_pipeline_stages`, and `crm_stage_history`.
- Add repositories and services for pipeline CRUD, stage reorder/archive/remap, and stage moves.
- Keep existing `opportunities.stage` until migration/read-model compatibility is proven.
- Add typed command: `crm.opportunity.move_stage`.

**Frontend:**
- Add pipeline selector, list view toggle, stage age, card count, and stage remap/admin surface.
- Keep inbound lease-option and outbound probate as separate default pipelines.

**Verification:**
- migration tests or repository tests for stage remap behavior
- focused API tests for stage move events
- Mission Control pipeline UI tests

## Phase 3: Owner, Property, Contact, And Opportunity Graph

**Outcome:** Ares models real-estate identities correctly instead of flattening everything into contacts.

**Backend:**
- Add canonical owners, properties, phone numbers, addresses, entity links, and source records.
- Preserve separate owner, property, contact, and opportunity identities.
- Add owner/property dedupe and relationship services.
- Add source record resolution workflow.

**Frontend:**
- Add Owners, Properties, and Contacts/Phonebook surfaces.
- Add linked entity panels on opportunity detail.
- Add top-owner-by-property-count views.

**Verification:**
- identity resolution tests
- owner/property link tests
- tenant isolation tests
- UI tests for linked detail navigation

## Phase 4: Multi-Entity Tasks, Reminders, Notes, And Activity

**Outcome:** Operators and agents can attach work to the correct business object and see one timeline.

**Backend:**
- Add task associations for owners, properties, contacts, opportunities, runs, and sessions.
- Add reminder policy fields and scheduled reminder events.
- Add normalized `crm_activity_events` read/write model.
- Add notes linked to multiple entities.

**Frontend:**
- Add unified activity timeline.
- Add task/reminder panels to every detail workspace.
- Add filters for assignee, due date, status, linked entity, and source lane.

**Verification:**
- multi-association task tests
- reminder schedule/escalation tests
- timeline aggregation tests
- Tasks page UI tests

## Phase 5: Agent Workbench Inside CRM

**Outcome:** The operator can spawn useful scoped agents from the dashboard, pipeline, or record detail page.

**Backend:**
- Add typed CRM agent commands:
  - `crm.research.start`
  - `crm.research.record_finding`
  - `crm.task.create`
  - `crm.activity.append`
  - `crm.owner.resolve`
  - `crm.property.resolve`
- Link agent runs to owners, properties, opportunities, and research sessions.
- Preserve approval gates for high-risk actions.

**Frontend:**
- Add "Run agent" actions on dashboard cards and detail pages.
- Show active agent run status and output artifacts inline.
- Add research findings and proposed actions panel.

**Verification:**
- agent command permission tests
- run-to-entity link tests
- approval-gated action tests
- UI tests for spawned run visibility

## Phase 6: Research Cockpit

**Outcome:** Ares has a native research surface for owner/property enrichment before map UI exists.

**Backend:**
- Add research sessions, source records, findings, confidence, evidence links, and review states.
- Support batch research jobs and Activity Center visibility.

**Frontend:**
- Add Research page.
- Add owner/property research queues.
- Add evidence review and promote-to-record actions.

**Verification:**
- research session lifecycle tests
- source record promotion tests
- UI tests for research queue and finding review

## Phase 7: Map-Ready Expansion

**Outcome:** The system can support a REISift/SiftMap-style UI when needed.

**Backend:**
- Add geocoded property coordinates.
- Add farm areas and polygon metadata.
- Add map source snapshots.
- Add comparable sale records if a comps workflow is selected.

**Frontend:**
- Add map view only after CRM graph and research cockpit are stable.
- Initial map should support property search, saved farm areas, and filtered source pulls.

**Verification:**
- geospatial data tests
- farm-area persistence tests
- map component browser verification when implemented

## Sequencing Recommendation

Start with Phase 1 and Phase 2 in the next implementation branch. They create the visible CRM flow and pipeline semantics without taking on the entire owner/property graph at once.
