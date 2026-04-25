# Ares CRM Control Plane Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans before implementation. This roadmap is a product/specification plan, not an execution checklist with code steps.

**Goal:** Turn Ares Mission Control into a CRM-backed business control plane for real-estate operations and agent supervision.

**Architecture:** Keep Ares as the deterministic runtime and source of truth. Extend Mission Control into a CRM shell, add Records as the high-volume prospecting/inventory layer, then add pipeline configuration, activity/timeline models, task/reminder associations, and scoped agent workbench actions.

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
- Extend `/mission-control/dashboard` read model to include record stats, stale opportunities, opportunities without next task, due reminders placeholder, provider failures, and active agent run cards.
- Extend `/mission-control/lead-machine`, `/mission-control/tasks`, `/mission-control/runs`, and `/mission-control/inbox` into reusable CRM read-model inputs.
- Add tests around read-model aggregation from current repositories.

**Frontend:**
- Upgrade `DashboardPage`, `PipelinePage`, `TasksPage`, and `InboxPage`.
- Add a lightweight `RecordsPage` shell backed by current lead/probate/source data if canonical record tables are not created yet.
- Add `OpportunitiesPage` if the existing `PipelinePage` is too narrow.
- Keep styling aligned with `docs/design/ares-dashboard-theme-2026-04-25.md`.

**Verification:**
- `uv run pytest tests/api/test_mission_control.py tests/services/test_mission_control_service.py -q`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`

## Phase 2: Records Registry And Records Workspace

**Outcome:** Ares has a first-class place where imported, researched, and acquired records live before they become opportunities.

**Backend:**
- Add migrations for `crm_records`, `crm_source_records`, `crm_record_source_memberships`, `crm_record_links`, `crm_record_status_history`, `crm_record_saved_views`, and `crm_record_promotions`.
- Model built-in record types: `property_record`, `owner_record`, `contact_record`, `probate_case_record`, and `tax_delinquency_record`.
- Preserve source evidence and list/source memberships when records are deduped.
- Add record status values for `new`, `incomplete`, `clean`, `needs_skip_trace`, `marketable`, `suppressed`, `promoted`, and `archived`.
- Add typed commands:
  - `crm.record.import`
  - `crm.record.create`
  - `crm.record.update_status`
  - `crm.record.suppress`
  - `crm.record.promote_to_opportunity`

**Frontend:**
- Add `RecordsPage` with tabs for All, Property, Owner, Contact, Incomplete, Suppressed, Marketable, and Promoted.
- Add saved filters for stacked records, vacant, tax delinquent, probate, high equity, no phone, skip traced with no numbers, owner with multiple properties, DNC/opt-out, and stale records.
- Add row indicators for data quality, source/list memberships, phone status, task status, assignee, marketing attempts, and promotion state.
- Add bulk actions for assign, tag, suppress, queue skip trace, create task, run research agent, and promote.

**Verification:**
- migration/repository tests for record create, dedupe, source membership preservation, saved views, and promotion history
- API tests for record import/update/suppress/promote commands
- Mission Control Records page UI tests

## Phase 3: Configurable Pipelines And Stage History

**Outcome:** Opportunities are no longer constrained to hard-coded enum stages only.

**Backend:**
- Add migrations for `crm_pipelines`, `crm_pipeline_stages`, and `crm_stage_history`.
- Add repositories and services for pipeline CRUD, stage reorder/archive/remap, and stage moves.
- Keep existing `opportunities.stage` until migration/read-model compatibility is proven.
- Add typed command: `crm.opportunity.move_stage`.
- Link opportunity creation to record promotion where applicable.

**Frontend:**
- Add pipeline selector, list view toggle, stage age, card count, and stage remap/admin surface.
- Keep inbound lease-option and outbound probate as separate default pipelines.

**Verification:**
- migration tests or repository tests for stage remap behavior
- focused API tests for stage move events
- Mission Control pipeline UI tests

## Phase 4: Owner, Property, Contact, And Opportunity Graph

**Outcome:** Ares models real-estate identities correctly instead of flattening everything into contacts.

**Backend:**
- Add canonical owners, properties, phone numbers, addresses, entity links, and source records.
- Preserve separate owner, property, contact, and opportunity identities.
- Add owner/property dedupe and relationship services.
- Add source record resolution workflow.
- Resolve records into owners, properties, contacts, and opportunities without deleting the record inventory history.

**Frontend:**
- Add Owners, Properties, and Contacts/Phonebook surfaces.
- Add linked entity panels on opportunity detail.
- Add top-owner-by-property-count views.

**Verification:**
- identity resolution tests
- owner/property link tests
- tenant isolation tests
- UI tests for linked detail navigation

## Phase 5: Multi-Entity Tasks, Reminders, Notes, And Activity

**Outcome:** Operators and agents can attach work to the correct business object and see one timeline.

**Backend:**
- Add task associations for records, owners, properties, contacts, opportunities, runs, and sessions.
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

## Phase 6: Agent Workbench Inside CRM

**Outcome:** The operator can spawn useful scoped agents from the dashboard, pipeline, or record detail page.

**Backend:**
- Add typed CRM agent commands:
  - `crm.record.clean`
  - `crm.record.dedupe`
  - `crm.record.enrich`
  - `crm.record.propose_promotion`
  - `crm.research.start`
  - `crm.research.record_finding`
  - `crm.task.create`
  - `crm.activity.append`
  - `crm.owner.resolve`
  - `crm.property.resolve`
- Link agent runs to records, owners, properties, opportunities, and research sessions.
- Preserve approval gates for high-risk actions.

**Frontend:**
- Add "Run agent" actions on dashboard cards, record rows, and detail pages.
- Show active agent run status and output artifacts inline.
- Add research findings and proposed actions panel.

**Verification:**
- agent command permission tests
- run-to-entity link tests
- approval-gated action tests
- UI tests for spawned run visibility

## Phase 7: Research Cockpit

**Outcome:** Ares has a native research surface for owner/property enrichment before map UI exists.

**Backend:**
- Add research sessions, source records, record links, findings, confidence, evidence links, and review states.
- Support batch research jobs and Activity Center visibility.

**Frontend:**
- Add Research page.
- Add record, owner, and property research queues.
- Add evidence review and promote-to-record actions.

**Verification:**
- research session lifecycle tests
- source record promotion tests
- UI tests for research queue and finding review

## Phase 8: Map-Ready Expansion

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

Start with Phase 1 and Phase 2 in the next implementation branch. They create the visible CRM shell and the missing Records foundation before deeper pipeline, owner/property graph, or map work.
