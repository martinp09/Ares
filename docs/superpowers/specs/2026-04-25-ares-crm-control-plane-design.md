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

Turn Ares Mission Control into a functional CRM-like operating system for the business: records, pipelines, opportunities, dashboards, activities, tasks, reminders, owner/property research, and agent supervision in one native UI.

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

3. **Records are the inventory layer.**
   Records are where high-volume prospecting, import cleanup, enrichment, filtering, suppression, skip tracing, marketing attempts, and lead promotion happen. Opportunities are created only when a record has become active deal work.

4. **Pipelines are configurable but governed.**
   Operators can create, reorder, archive, and remap stages, but every change preserves history.

5. **Activities are append-only truth.**
   If a human, provider, or agent changes meaningful state, a timeline event exists.

6. **Tasks can attach wherever work happens.**
   A task can link to a record, owner, property, contact, opportunity, run, or agent session.

7. **Research is a workflow, not a note dump.**
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

- `SourceRecord`: raw imported or researched payload with source, extraction time, confidence, and original data.
- `Record`: canonical prospecting/inventory object created from one or more source records; records are the default place for imported lists, SiftMap-style pulls, probate rows, tax rows, inbound submissions before qualification, skip-trace results, and marketing eligibility state.
- `RecordType`: built-in record type such as `property_record`, `owner_record`, `contact_record`, `probate_case_record`, `tax_delinquency_record`, or future custom record types.
- `RecordStatus`: data/work state such as `new`, `incomplete`, `clean`, `needs_skip_trace`, `marketable`, `suppressed`, `promoted`, or `archived`.
- `RecordSourceMembership`: source/list/campaign/farm-area membership so one record can be stacked across multiple lists without duplication.
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

Outbound probate should not place every imported probate row directly into the pipeline. The pipeline starts after a record is promoted from the Records workspace into active opportunity work.

1. Promoted from records
2. Contact candidate ready
3. Outreach drafted
4. Human approved
5. Outreach active
6. Reply needs review
7. Seller qualified
8. Offer path selected
9. Contract sent
10. Contract signed
11. Title open
12. Curative review
13. Dispo ready
14. Closed
15. Dead / suppressed

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
- Records
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

- total records, new records, incomplete records, records needing skip trace, records with no phone, and records promoted this period
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

### Records Workspace

Records is the high-volume inventory and prospecting area. It is not the pipeline and it is not a raw import log.

Records must support:

- tabs for All Records, Property Records, Owner Records, Contact Records, Incomplete, Suppressed, Marketable, and Promoted
- saved filter presets for stacked records, vacant, tax delinquent, probate, high equity, no phone, skip traced with no numbers, owner with multiple properties, DNC/opt-out, and stale records
- filters by list, tag, source, county, property status, owner type, phone status, phone count, email count, skip trace status, marketing attempts, task status, assignee, distressor, upload date, last updated date, and promotion state
- bulk actions for assign, tag, suppress, queue skip trace, send to research, create tasks, create marketing draft, export, and promote to opportunity
- row-level data quality indicators for incomplete owner, incomplete mailing address, missing property facts, no phone, duplicate candidate, stale source, and low-confidence match
- quick record detail with linked owner, property, contacts, source memberships, tasks, activity, research findings, and promotion history
- agent actions for clean record, dedupe, enrich owner, find phones, classify distress, summarize evidence, and propose promotion

Records live in Supabase as canonical CRM records, not only inside provider payloads, agent memory, lead events, or import files.

### Pipeline Board

The board should support active opportunities only:

- configurable pipeline selector
- stage columns
- card movement with append-only stage history
- stage age / SLA badges
- owner, property, source lane, strategy lane, assignee, value, and next task on cards
- filters by source lane, assignee, tag, status, county, owner type, phone status, task state, and agent state
- list view for bulk cleanup

### Detail Workspace

Every record, owner, property, contact, and opportunity should share a three-panel detail pattern:

- left: identity facts and linked entities
- center: timeline, conversations, notes, evidence, and research findings
- right: tasks, reminders, agent actions, files, stage controls, and quick commands

### Agent Workbench

From dashboard, pipeline, or detail pages, the operator should be able to spawn scoped agent work:

- clean records
- dedupe records
- enrich records
- promote/suppress records
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

Use current tables and services to create read models for dashboard, records, pipeline, tasks, runs, approvals, and inbox. Avoid schema churn until the UI shape is accepted.

### Phase 2: Records Registry

Add Supabase migrations and repositories for canonical records, source payloads, record source memberships, record links, record statuses, data quality flags, saved record views, and promotion history.

Records are the first CRM graph table family because owners, properties, contacts, and opportunities should be resolvable from record inventory instead of bypassing it.

### Phase 3: Canonical CRM Graph

Add Supabase migrations and repositories for owners, properties, phone numbers, entity associations, configurable pipelines, stages, stage history, task associations, reminders, activities, and notes.

### Phase 4: Agent-To-CRM Command Surface

Expose typed commands for agent-safe CRM work:

- `crm.record.import`
- `crm.record.create`
- `crm.record.update_status`
- `crm.record.apply_saved_view`
- `crm.record.promote_to_opportunity`
- `crm.record.suppress`
- `crm.owner.resolve`
- `crm.property.resolve`
- `crm.opportunity.create`
- `crm.opportunity.move_stage`
- `crm.task.create`
- `crm.reminder.schedule`
- `crm.activity.append`
- `crm.research.start`
- `crm.research.record_finding`

### Phase 5: Map-Ready Research

Prepare geocoding, saved farm areas, polygon source pulls, and comparable-sale data. Build the map only after owner/property/opportunity workflows are stable.

## Data Rules

- Stage movement must preserve `from_stage`, `to_stage`, actor, timestamp, reason, source command, and prior SLA state.
- Stage deletion must require remapping active opportunities.
- Records live in canonical Supabase CRM tables and can be linked to source payloads, owners, properties, contacts, opportunities, tasks, activities, and agent runs.
- Imported/source payloads do not become opportunities directly; they become records first, then records can be promoted when qualification rules are met.
- A record can exist without an opportunity; an opportunity should usually point back to the promoted record that created it.
- Record dedupe must preserve source memberships and evidence rather than dropping duplicate source rows.
- Phone status and call disposition must be different fields.
- Owner marketing attempts and property marketing attempts must be counted separately.
- Every task must support at least one association and may support multiple associations, including records.
- Every research finding must cite a source record or explicit agent evidence.
- Provider callbacks and agent runs must be visible as activities.
- Outreach sends and public/transmitted actions require explicit approval when policy marks them risky.

## Implementation Roadmap

1. Create CRM shell read models from existing Ares state.
2. Add Records overview/read-model surface using current lead/probate/source data where available.
3. Add canonical records registry, saved views, filters, source memberships, and promotion history.
4. Build dashboard and pipeline UI around records plus active opportunities.
5. Add canonical pipeline/stage config and stage history.
6. Add owners/properties/contacts graph and detail workspaces.
7. Add multi-entity tasks, reminders, notes, and normalized activity timeline.
8. Add scoped agent spawn actions and research sessions.
9. Add owner/property research cockpit.
10. Add map-backed farm-area research as the first optional expansion.

## Open Decisions

1. Whether `business_id + environment` remains the primary tenant key through this slice or `org_id` becomes required everywhere.
2. Whether the first UI implementation should target current fixture-backed Mission Control read models first or immediately add new Supabase-backed CRM tables.
3. Whether map research should use an embedded map vendor in phase 2 or remain a structured data-only research cockpit until phase 3.
4. Whether record types should stay limited to built-in real-estate types for the first slice or include a HighLevel-style custom object builder later.
5. Whether pipeline stage names should be seeded as defaults or fully admin-configured from the start.

## Recommendation

Use an incremental hybrid:

1. Branch keeps the current production runtime untouched.
2. First implementation pass builds the dashboard and Records shell over existing data and fixtures.
3. Second pass introduces canonical record migrations behind repositories and read models.
4. Third pass adds pipeline/stage configuration and opportunity promotion from records.
5. Fourth pass embeds agent workbench and research workflows into record/opportunity detail pages.
6. Map work stays model-ready but UI-deferred.

This gives the operator a usable CRM/control plane quickly while avoiding a schema-first detour before the actual workflow is visible.
