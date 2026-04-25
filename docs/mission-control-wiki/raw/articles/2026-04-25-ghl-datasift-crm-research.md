---
title: "Go High Level and DataSift CRM Research for Ares"
created: 2026-04-25
type: source-note
tags: [ares, crm, mission-control, go-high-level, datasift, reisift, real-estate]
sources:
  - https://help.gohighlevel.com/support/solutions/articles/155000001982-understanding-pipelines
  - https://help.gohighlevel.com/support/solutions/articles/155000001983
  - https://help.gohighlevel.com/support/solutions/articles/155000003261-workflow-trigger-task-reminder
  - https://help.gohighlevel.com/support/solutions/articles/155000006643-tasks-across-multiple-objects
  - https://help.gohighlevel.com/support/solutions/articles/155000006651-the-contact-details-page
  - https://help.gohighlevel.com/support/solutions/articles/155000001241-how-to-filtering-opportunities
  - https://help.gohighlevel.com/support/solutions/articles/155000007649-opportunity-forecasting
  - https://help.gohighlevel.com/support/solutions/articles/155000003896-getting-started-with-custom-objects
  - https://help.gohighlevel.com/support/solutions/articles/155000003897-creating-and-editing-custom-objects
  - https://help.gohighlevel.com/support/solutions/articles/155000004023-creating-and-updating-custom-object-records
  - https://www.datasift.ai/features/owner-records
  - https://intercom.help/reisift/en/articles/9519141-getting-started-with-siftmap
  - https://intercom.help/reisift/en/articles/6516091-owner-records-overview
  - https://intercom.help/reisift/en/articles/6209588-filter-records-overview
  - https://intercom.help/reisift/en/articles/13251458-dashboard-overview
  - https://intercom.help/reisift/en/articles/6640844-siftline-overview
  - https://intercom.help/reisift/en/articles/6449998-property-details-vs-owner-details
  - https://intercom.help/reisift/en/articles/6350615-activity-page-overview
  - https://intercom.help/reisift/en/articles/6418251-statuses-explained
  - https://youtu.be/YMHJ9jvoKjY
  - https://youtu.be/PsOvaf2-CTI
---

# Go High Level and DataSift CRM Research for Ares

## Why This Matters

Ares already has production-backed runtime state, provider callbacks, lead-machine write paths, managed agents, tasks, opportunities, and Mission Control read models. The missing product layer is a unified operator CRM/control plane that lets the owner run the business, supervise agents, and manage real-estate opportunities without treating agents as a separate tool silo.

The best model is not a generic CRM clone. The useful shape is:
- Go High Level for opportunity, pipeline, stage, dashboard, communication, task, reminder, and automation semantics.
- DataSift/REISift for records as the high-volume prospecting inventory, real-estate owner/property/contact separation, property statuses, filtering, SiftMap-style research, and bulk activity visibility.
- Ares for deterministic runtime, typed commands, approvals, agent runs, provider adapters, and Supabase-backed audit.

## Go High Level Patterns Worth Pulling

### Opportunities

HighLevel defines an opportunity as the active deal object that moves through a pipeline. It stores contact information, value, notes, tasks, and activity history, and supports default statuses: open, won, lost, and abandoned.

Ares implication:
- Keep `Opportunity` as the moving business process, not as a duplicate contact.
- Add configurable opportunity statuses and lost/abandoned reasons.
- Preserve notes, tasks, communications, and stage history on the opportunity.
- Let one contact/owner/property participate in multiple opportunities when the business process genuinely differs.

### Records And Custom Objects

HighLevel's newer Custom Objects model treats non-contact business entities as first-class CRM records with fields, associations, workflows, forms, reporting, and dashboards. It specifically calls out real-estate properties as a good use case and warns against cramming unrelated data into Contacts or Opportunities. Custom object records can be created, updated, imported, related to other objects, and used as workflow triggers.

Ares implication:
- Records cannot be only hidden import plumbing; Ares needs a visible `Records` section.
- Ares should not make arbitrary custom object building the first slice, but it should adopt the same principle: records are first-class typed objects with their own fields, lifecycle, associations, and automation triggers.
- Real-estate `Record` is the canonical inventory object for prospecting and data hygiene before something becomes an `Opportunity`.
- `PropertyRecord`, `OwnerRecord`, and future custom record types should be queryable from one Records workspace.
- Records need import, update, related-object association, filtering, dashboarding, and workflow hooks.

### Pipelines And Stages

HighLevel pipelines are visual workflows composed of stages. Stages need clear action meaning, safe reorder/archive/delete behavior, reporting visibility, and stage-based automation.

Ares implication:
- Replace fixed enum-only stages with tenant-configured pipelines and ordered stages.
- Keep phase and stage changes append-only for history and reporting.
- A stage delete/archive action must remap active opportunities instead of dropping state.
- Stage transitions should be event triggers for tasks, reminders, approvals, and agent runs.

### Dashboard And Forecasting

HighLevel uses pipeline reporting to expose drop-off, stage duration, win rate, expected close timing, weighted revenue, and data hygiene risk.

Ares implication:
- Dashboard cards should answer "what needs action today" before they show generic totals.
- Forecasting should become "contract probability / assignment probability / expected profit" instead of generic sales revenue.
- Data hygiene cards should surface missing owner info, missing phone status, stale stage, no next task, failed provider callback, or low-confidence research.

### Contacts, Activities, Notes, And Tasks

HighLevel contact detail pages combine contact facts, conversations, activities, opportunities, tasks, notes, appointments, documents, and payments. Newer HighLevel task behavior allows one task to link to contacts, opportunities, companies, and custom objects. Task reminders can trigger workflows before or after due dates.

Ares implication:
- Build one record detail workspace with left identity facts, center timeline/conversation/activity, and right action modules.
- Support multi-entity tasks linked to owners, contacts, properties, opportunities, runs, and agent sessions.
- Reminders should be first-class scheduled events with escalation and workflow hooks.
- Notes should be structured enough to link evidence, documents, comps, call summaries, and agent findings.

### Tutorial Signal From YouTube Resources

The first linked video is a 1:06:20 beginner walkthrough with chapters for Dashboard, Contacts, Conversations, Calendars, Opportunities, Payments, AI Agents, Marketing, Automation, Sites, Memberships, Media Storage, Reputation, and Settings.

The second linked video is a 2:36:45 full course with chapters for subaccounts/snapshots, prospecting and marketing reports, contacts and automations, pipeline management, payments/invoices, email marketing, automations, funnels/sites, and membership courses.

The durable product lesson is that Go High Level flows because contacts, conversations, calendars, opportunities, payments, marketing, AI agents, and automations are surfaced inside one operating shell. For Ares, the equivalent should be owners/properties/opportunities/tasks/agents/research/runs inside one Mission Control shell.

## DataSift / REISift Patterns Worth Pulling

### Records Workspace

REISift centers prospecting around the Records page. Records are where uploaded or acquired data lives before it becomes a lead-management board card. REISift filters records by lists, tags, phone status, phone type, skip trace state, absentee/vacant flags, DNC/opt-out, task count, property fields, owner fields, marketing attempts, offers, distressor fields, and saved filter presets. Its SiftLine board is explicitly for managing records after they become leads, not for prospecting or high-volume record management.

Ares implication:
- `Records` must be its own top-level Mission Control area.
- Records are the high-volume inventory/prospecting layer; opportunities and pipeline boards are the lower-volume deal execution layer.
- Records should support saved views and filters before pipeline promotion.
- A record can be marketable, incomplete, suppressed, skip-trace needed, no-number, stacked, vacant, distressed, owned-by-multiple-property owner, or promoted.
- Agents should be able to operate against records directly: clean, enrich, dedupe, classify, find contacts, suggest promotion, or suppress.
- Ares dashboard should include record stats like total records, new records, incomplete records, records with no phone, records needing skip trace, records by list/source, and records promoted to opportunities.

### Owner Records

DataSift owner records separate owners from properties, classify owners as person, company, or trust, expose property count, and support owner-level marketing attempts.

Ares implication:
- Add a canonical `Owner` entity separate from `Property` and `Contact`.
- Track owner type: person, company, trust, estate, unknown.
- Make "owners with multiple properties" a first-class prospecting view.
- Track owner-level marketing attempts separately from property-level attempts.

### Property And Owner Details

REISift separates property details from owner details. Property detail contains occupancy, assignee, property status, property temperature, map/gallery, files, tasks, structure characteristics, land, tax, sale, lien, probate, foreclosure, bankruptcy, divorce, mortgage, ownership, and direct mail details.

Ares implication:
- Property detail is the asset workspace.
- Owner detail is the decision-maker/contactability workspace.
- Opportunity detail is the current deal process.
- The UI must let operators traverse all three without losing context.

### Phonebook And Phone Status

REISift phonebook focuses on contacts. Phone statuses distinguish correct, wrong, no answer, DNC, dead, and primary phone.

Ares implication:
- Phone status must remain separate from call disposition.
- Contact/phonebook records should support buyers, agents, lenders, contractors, brokers, and other reusable relationship types.
- Ares should never repeatedly market the same owner because multiple property records share a decision-maker.

### Activity, Bulk Work, And SiftMap

REISift activity tracks uploads, downloads, skip tracing, predictive dialer, direct mail, and account actions with statuses like enqueued, processing, complete, and failed. SiftMap supports nationwide data search, property/owner details, polygon selection, virtual driving for dollars, route planning, and pulling filtered records into the account.

Ares implication:
- Bulk jobs need an Activity Center visible to the operator and agents.
- Map research is a phase-2 feature, but the data model should be ready for geocoded properties, farm areas, polygons, comps, and source snapshots.
- Research imports should create raw source records first, then resolve to properties, owners, contacts, and opportunities.

## Fit With Current Ares

Current Ares already has:
- `app/models/opportunities.py` with source lanes and fixed stages.
- `supabase/migrations/202604160002_runtime_opportunities.sql` with tenant-scoped opportunities.
- `app/models/tasks.py` plus task persistence aligned around lead IDs.
- lead events and append-only event patterns.
- Mission Control pages for dashboard, inbox, approvals, runs, agents, catalog, settings, tasks, and pipeline.

Gaps for the CRM/control-plane slice:
- records are not yet modeled as a first-class visible inventory/prospecting workspace.
- current `SourceRecord` language is too raw/import-oriented and does not cover the operator-facing record lifecycle.
- the product needs a clear rule that records live before opportunities, while opportunities only represent active deal processes.
- pipelines and stages are not configurable records yet.
- opportunity stage history is not first-class.
- tasks are not multi-entity associations yet.
- owners/properties are not canonical CRM graph entities.
- activity timelines are split across lead events, runs, tasks, messages, and audit instead of normalized read models.
- Mission Control pipeline is a summary board, not a working CRM board.
- no owner/property research workbench or map-backed source acquisition exists yet.

## Recommended Product Direction

Build Ares as a CRM-backed control plane:
- Records own the prospecting inventory and data hygiene workflow.
- Opportunities own the active deal process after promotion from records or direct inbound qualification.
- CRM primitives own the business state.
- Mission Control owns operator interaction.
- Agents work through typed commands against the CRM graph.
- Every agent run, stage change, task update, provider event, and research import lands in the same activity model.
- Map/SiftMap-style research is prepared in the model but implemented after the core CRM workflow is stable.
