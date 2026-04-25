---
title: "Ares CRM Control Plane Design"
status: draft-for-review
created: 2026-04-25
updated: 2026-04-25
branch: feature/ares-crm-control-plane-planning
sources:
  - docs/mission-control-wiki/raw/articles/2026-04-25-ghl-datasift-crm-research.md
  - docs/superpowers/specs/2026-04-19-ares-crm-blueprint.md
  - docs/mission-control-wiki/concepts/ares-crm-control-plane.md
---

# Ares CRM Control Plane Design

## Goal

Turn Ares Mission Control into a functional CRM-like operating system for the business: pipelines, opportunities, dashboards, activities, tasks, reminders, owner/property research, and agent supervision in one native UI.

This is not a generic CRM clone. Ares should behave like Go High Level where that helps with flow, and like DataSift/REISift where that helps real-estate operations, while keeping Ares as the deterministic runtime and source of truth.

## Non-Goals For This Slice

- No Supabase production schema changes until this spec is approved.
- No map UI in the first implementation slice.
- No replacement of Hermes or Trigger; Ares remains the runtime and Mission Control remains the operator cockpit.
- No merging outbound probate and inbound lease-option lanes into one ambiguous funnel.

## Product Principles

1. **CRM state drives agent work.**
   Agents should read and write typed CRM records, not private scratchpads.

2. **Opportunities are the moving business object.**
   Owners, properties, contacts, records, and companies are linked entities; opportunities are the active deal/work process.

3. **Pipelines are configurable but governed.**
   Operators can create, reorder, archive, and remap stages, but every change preserves history.

4. **Activities are append-only truth.**
   If a human, provider, or agent changes meaningful state, a timeline event exists.

5. **Tasks can attach wherever work happens.**
   A task can link to an owner, property, contact, opportunity, run, or agent session.

6. **Research is a workflow, not a note dump.**
   Research findings become source records, evidence, owner/property facts, or proposed actions.

## Core Domain Model

### Tenant And Actor Layer

- `Organization`: tenant boundary for the business.
- `Workspace`: operating area inside an organization if needed later.
- `User`: human operator.
- `Agent`: deployable agent product unit.
- `Actor`: common wrapper for users, agents, and provider callbacks.
- `Role`: governs UI visibility and command permissions.

### CRM Graph

- `SourceRecord`: raw imported or researched record with source, extraction time, confidence, and payload.
- `Owner`: legal or human decision-maker; type is person, company, trust, estate, or unknown.
- `Property`: physical asset with address, parcel data, occupancy, valuation, tax, mortgage, lien, probate, foreclosure, bankruptcy, divorce, and MLS fields as structured extensions.
- `Contact`: reachable person/channel record; includes phone/email/mailing methods, consent, status, and relationship type.
- `PhoneNumber`: contactability primitive with phone status separate from call outcomes.
- `CompanyEntity`: LLC, trust, estate, lender, buyer entity, or vendor.
- `Opportunity`: active business process linked to one or more owners/properties/contacts.
- `Pipeline`: ordered workflow for a lane or strategy.
- `PipelineStage`: ordered stage with entry rules, reporting visibility, SLA thresholds, and automation hooks.
- `StageHistory`: append-only opportunity movement ledger.

### Work And Timeline

- `ActivityEvent`: normalized activity across provider events, human actions, agent runs, imports, exports, notes, stage moves, and bulk jobs.
- `CommunicationEvent`: call, SMS, email, direct mail, voicemail, or conversation item.
- `Task`: work item with status, priority, due date, reminder policy, recurrence policy, assignee, and entity associations.
- `Reminder`: scheduled task notification or escalation.
- `Note`: rich-enough internal note linked to one or more entities.
- `FileAttachment`: document, image, mailer, contract, title packet, or generated artifact.
- `BulkActivity`: import, export, skip trace, direct mail, map pull, batch update, or agent batch run.

### Research And Map Readiness

- `ResearchSession`: scoped research run launched by user or agent.
- `ResearchFinding`: evidence-backed fact or recommendation produced by research.
- `FarmArea`: saved geography or polygon for future map workflows.
- `GeoPoint`: normalized property coordinate.
- `ComparableSale`: future comps support.

## Default Pipelines

### Inbound Lease-Option Pipeline

1. New inbound lead
2. Contact attempted
3. Call booked
4. Seller qualified
5. Offer path selected
6. Contract sent
7. Contract signed
8. Title open
9. Dispo ready
10. Closed
11. Dead / disqualified

### Outbound Probate Pipeline

1. Source record imported
2. Owner/property resolved
3. Keep-now qualified
4. Contact candidate ready
5. Outreach drafted
6. Human approved
7. Outreach active
8. Reply needs review
9. Seller qualified
10. Offer path selected
11. Contract sent
12. Contract signed
13. Title open
14. Curative review
15. Dispo ready
16. Closed
17. Dead / suppressed

### Acquisition / Contract-To-Close Skeleton

This can start as a shared sub-pipeline visible from opportunities after contract signed:

1. Contract signed
2. Earnest money / option fee confirmed
3. Title opened
4. Seller docs requested
5. Curative issue found
6. Curative issue resolved
7. Buyer / exit strategy assigned
8. Closing scheduled
9. Closed

## Mission Control UI

### Navigation

The UI should keep the existing Mission Control shell and add CRM-first surfaces:

- Dashboard
- Pipeline
- Opportunities
- Owners
- Properties
- Contacts / Phonebook
- Research
- Tasks
- Activity
- Inbox
- Agents
- Runs
- Approvals
- Settings

### Dashboard

Dashboard must lead with decisions and exceptions:

- due tasks today
- overdue reminders
- stale stages
- new replies needing review
- opportunities without next task
- provider callback failures
- active agent runs
- agent runs needing approval
- top owners by property count
- missing phone status / DNC risk
- pipeline stage counts and stage aging

### Pipeline Board

The board should support:

- configurable pipeline selector
- stage columns
- card movement with append-only stage history
- stage age / SLA badges
- owner, property, source lane, strategy lane, assignee, value, and next task on cards
- filters by source lane, assignee, tag, status, county, owner type, phone status, task state, and agent state
- list view for bulk cleanup

### Detail Workspace

Every owner, property, contact, and opportunity should share a three-panel detail pattern:

- left: identity facts and linked entities
- center: timeline, conversations, notes, evidence, and research findings
- right: tasks, reminders, agent actions, files, stage controls, and quick commands

### Agent Workbench

From dashboard, pipeline, or detail pages, the operator should be able to spawn scoped agent work:

- research owner
- research property
- find contact candidates
- draft outreach
- summarize timeline
- prepare seller call brief
- inspect title/curative risk
- suggest next task
- audit stale opportunity
- run batch cleanup proposal

High-risk actions stay approval-gated.

## Backend Architecture

### Phase 1: Read-Model First CRM Shell

Use current tables and services to create read models for dashboard, pipeline, tasks, runs, approvals, and inbox. Avoid schema churn until the UI shape is accepted.

### Phase 2: Canonical CRM Graph

Add Supabase migrations and repositories for owners, properties, phone numbers, entity associations, configurable pipelines, stages, stage history, task associations, reminders, activities, and notes.

### Phase 3: Agent-To-CRM Command Surface

Expose typed commands for agent-safe CRM work:

- `crm.owner.resolve`
- `crm.property.resolve`
- `crm.opportunity.create`
- `crm.opportunity.move_stage`
- `crm.task.create`
- `crm.reminder.schedule`
- `crm.activity.append`
- `crm.research.start`
- `crm.research.record_finding`

### Phase 4: Map-Ready Research

Prepare geocoding, saved farm areas, polygon source pulls, and comparable-sale data. Build the map only after owner/property/opportunity workflows are stable.

## Data Rules

- Stage movement must preserve `from_stage`, `to_stage`, actor, timestamp, reason, source command, and prior SLA state.
- Stage deletion must require remapping active opportunities.
- Phone status and call disposition must be different fields.
- Owner marketing attempts and property marketing attempts must be counted separately.
- Every task must support at least one association and may support multiple associations.
- Every research finding must cite a source record or explicit agent evidence.
- Provider callbacks and agent runs must be visible as activities.
- Outreach sends and public/transmitted actions require explicit approval when policy marks them risky.

## Implementation Roadmap

1. Create CRM shell read models from existing Ares state.
2. Build dashboard and pipeline UI around current data.
3. Add canonical pipeline/stage config and stage history.
4. Add owners/properties/contacts graph and detail workspaces.
5. Add multi-entity tasks, reminders, notes, and normalized activity timeline.
6. Add scoped agent spawn actions and research sessions.
7. Add owner/property research cockpit.
8. Add map-backed farm-area research as the first optional expansion.

## Open Decisions

1. Whether `business_id + environment` remains the primary tenant key through this slice or `org_id` becomes required everywhere.
2. Whether the first UI implementation should target current fixture-backed Mission Control read models first or immediately add new Supabase-backed CRM tables.
3. Whether map research should use an embedded map vendor in phase 2 or remain a structured data-only research cockpit until phase 3.
4. Whether pipeline stage names should be seeded as defaults or fully admin-configured from the start.

## Recommendation

Use an incremental hybrid:

1. Branch keeps the current production runtime untouched.
2. First implementation pass builds the CRM shell over existing data and fixtures.
3. Second pass introduces canonical CRM migrations behind repositories and read models.
4. Third pass embeds agent workbench and research workflows into the CRM detail pages.
5. Map work stays model-ready but UI-deferred.

This gives the operator a usable CRM/control plane quickly while avoiding a schema-first detour before the actual workflow is visible.
