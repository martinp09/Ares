---
title: "Ares CRM Master Scope"
status: draft
updated_at: "2026-04-19T00:00:00Z"
source_notes:
  - "HighLevel help docs: pipelines, opportunities, contact detail, activity, call status, tasks, custom fields"
  - "REISift help center: records, phonebook, statuses, SiftLine, sequences, activity, tasks, direct mail, SMS, imports, exports, SiftMap, settings"
  - "NakatomiCRM repo: auth, workspaces, schema discovery, import/export, files, relationships, dedupe/merge, webhooks, MCP"
  - "/root/wiki/queries/ares-backend-crm-primitives-synthesis.md"
  - "/root/wiki/comparisons/highlevel-vs-reisift-vs-nakatomi-for-ares.md"
---

# Ares CRM Master Scope

## Executive summary

Ares is the self-hosted operating system for distressed real-estate lead management.

It is not a generic CRM. It is the canonical record layer, workflow layer, and operator console for people, properties, owners, records, opportunities, and outreach activity.

The product shape comes from three source systems:

- **HighLevel** provides the CRM behavior model: pipelines, stages, opportunities, unified contact detail, tasks, activity timelines, call statuses, custom fields, and workflow triggers.
- **REISift** provides the real-estate operator model: raw records, phonebook separation, statuses, SiftLine, filters, boards, sequences, direct mail, SMS, skip tracing, credits, bulk actions, and market intelligence.
- **NakatomiCRM** provides reusable backend plumbing: auth, workspaces, schema discovery, import/export, files, relationships, dedupe/merge, webhooks, and MCP surfaces.

The point is not to clone any one product. The point is to fuse the useful parts into one system that owns the data, automates the grunt work, and only interrupts a human when a decision is actually needed.

## Product definition

### Ares is

- the system of record for lead and property operations
- the workflow engine for follow-up, outreach, assignment, and reactivation
- the audit layer for every meaningful state change
- the operator cockpit for moving records to decisions
- the canonical place where work is assigned, tracked, and measured

### Ares is not

- a generic dashboard CRM
- a vendor-dependent data wrapper
- a single-channel outreach tool
- a raw spreadsheet with nicer colors
- a pretty UI on top of broken state modeling

## Core principles

1. **Separate intake from execution.**
   Raw records are not the same thing as worked leads.

2. **Model each state explicitly.**
   Opportunity stage, property status, phone status, task status, and global status are different concepts.

3. **Every meaningful change is an event.**
   If it matters operationally, it belongs in the activity history.

4. **Channels are adapters.**
   SMS, dialers, direct mail, skip tracing, email, and calendar sync all feed the same CRM state model.

5. **Assignment is policy.**
   Ownership, visibility, and permissions shape the UI and the work queue.

6. **Segmentation is product, not garnish.**
   Tags, lists, presets, statuses, and filters are the operator workflow.

7. **Human interruption is a scarce resource.**
   Ares should only ask for decisions, approvals, or review when the machine cannot safely continue.

## Source-to-Ares synthesis

| Source | What it contributes | What Ares must keep |
|---|---|---|
| HighLevel | pipeline semantics, opportunities, timelines, tasks, call outcomes, custom fields | a real CRM state machine with visible stages and a unified record detail page |
| REISift | records vs phonebook vs board flow, statuses, filters, sequences, direct mail, skip trace, credits | real-estate lead operations instead of generic contact management |
| NakatomiCRM | auth, workspaces, schema discovery, import/export, files, relationships, dedupe/merge, webhooks, MCP | the plumbing that makes the system durable, portable, and extensible |

## Canonical domain model

### Tenancy and identity

- **Workspace**: tenant boundary and configuration root
- **User**: operator identity inside a workspace
- **Role / permission set**: what the user can see and do
- **API key / integration credential**: machine identity for external systems

### Core CRM graph

- **Person / Contact / Owner**: the human identity layer
- **Property**: the asset / address layer
- **Company / Entity**: LLCs, trusts, and other legal wrappers
- **Record**: raw intake object
- **Opportunity**: the actionable CRM object that moves through stages
- **Pipeline**: ordered opportunity flow
- **Stage**: a pipeline step with reporting and automation meaning
- **Board**: operational lead-management view
- **Board phase / column**: board lane for lead movement

### Operational memory

- **Task**: follow-up work item
- **Note**: lightweight operator memory
- **Activity event**: append-only audit history
- **Communication event**: normalized record of calls, SMS, email, mail, and dialer interactions
- **Call outcome / disposition**: what actually happened on the attempt
- **Phone number / phone status**: number-health model, distinct from call outcome

### Segmentation and automation

- **Tag**: flexible labeling primitive
- **List**: curated membership set
- **Filter preset**: reusable saved query
- **Workflow / sequence**: trigger-driven automation
- **Trigger / rule**: event condition
- **Integration connection**: provider configuration
- **Import job**: ingestion event
- **Export job**: portability event
- **File attachment**: uploaded or generated artifact
- **Notification**: operator-facing alert
- **Credit ledger / usage event**: cost tracking for enrichment and outreach

## State rules

### Opportunity state

An opportunity is the moving sales object. It can be open, won, lost, abandoned, or nurtured. It must preserve history when it changes stages or pipelines.

Rules:

- a stage change never deletes opportunity history
- a lost opportunity keeps a reason
- a stage can be archived or remapped without destroying historical meaning
- a pipeline can be default, custom, reordered, or archived
- stage reporting can hide or include stages without mutating the underlying opportunity record

### Phone status vs call disposition

These are not the same thing.

- **Phone status** = number quality / contactability
- **Call disposition** = what happened during an attempt

Example:
- a number can be `connected` but the call disposition can still be `not_interested`
- a number can be `wrong` or `disconnected` even when the attempt was logged correctly

### Record vs opportunity vs property

- a **record** is the intake object
- a **property** is the physical asset
- an **opportunity** is the active deal/lead process

One record may resolve to multiple historical activities, but the canonical graph should still be queryable as one identity chain.

## Functional scope by subsystem

### 1) Tenant, auth, and access control

Ares must support workspace boundaries, user roles, scoped visibility, and machine access for integrations.

Must include:

- workspace isolation
- user roles
- permission checks on every read/write surface
- integration credentials / API keys
- audit of permission-sensitive actions
- visibility rules that shape what a user can see in boards, timelines, and search results

### 2) Canonical CRM kernel

Ares must own the core graph for contacts, owners, properties, companies, records, opportunities, pipelines, and stages.

Must include:

- identity resolution
- ownership links
- custom fields
- canonical relationships
- searchable detail views
- history-preserving merges and dedupe
- entity-level timeline and task attachments

### 3) Pipelines, stages, opportunities, and boards

Ares must support both HighLevel-style opportunities and REISift-style lead boards.

Must include:

- pipelines with named stages
- reorderable / archivable stages
- move-stage actions
- stage visibility controls
- board phases / columns
- drag-and-drop card movement
- opportunity status transitions
- lost reasons and close outcomes
- stage history for reporting and automation

### 4) Activity, timelines, and communication history

Ares must store an append-only operational history for every meaningful event.

Must include:

- event log
- entity timelines
- call history
- SMS history
- email / mail / dialer history when applicable
- attempt counters
- activity filters by entity, user, channel, type, and date
- bulk job visibility in the history stream

### 5) Tasks, notes, assignments, and operator memory

Ares must unify task handling across contacts, properties, opportunities, and records.

Must include:

- task creation and completion
- recurring tasks
- task assignment
- notes on multiple entity types
- task queues and calendars
- due dates and reminders
- visibility based on ownership and role
- a unified task surface, not separate dead-end task silos

### 6) Segmentation, filtering, and saved views

Ares must make filtering a first-class product surface.

Must include:

- tags
- lists
- statuses
- phone statuses
- stages
- assignees
- attempt counts
- custom field filters
- any/all filter logic
- saved presets
- reusable segment definitions
- fast queryable board filters

### 7) Imports, exports, files, dedupe, and merge

Ares must support controlled ingestion and portability without losing identity history.

Must include:

- file upload / file attachment
- import mapping
- add vs update modes
- dedupe and merge workflows
- export jobs
- item-level import/export audit events
- schema discovery / introspection
- portability without vendor lock-in

### 8) Outreach channels and attempt tracking

Ares must normalize outbound and inbound communication across channels.

Must include:

- SMS
- dialer integration
- direct mail
- email where relevant
- click-to-call or provider-backed call events
- attempt counters per number and per record
- contact outcome tracking
- provider reference capture
- channel-specific status normalization

### 9) Workflow engine and sequences

Ares must automate follow-up and reactivation.

Must include:

- event-triggered workflows
- stage-change triggers
- stale-lead triggers
- call-status triggers
- tag/list triggers
- board-move triggers
- sequence enrollment and unenrollment
- idempotent action execution
- replay-safe workflows
- audit trails for trigger and action completion

### 10) Integrations, webhooks, and MCP

Ares must be easy to connect to other systems and agents.

Must include:

- durable webhook delivery
- webhook testing
- integration registration
- provider configuration
- MCP schema/tool exposure
- schema discovery for agent use
- permission-aware external access

### 11) Cockpit UI / Mission Control

Ares must expose a clean operator interface that makes the machine usable.

Must include:

- unified profile pages
- pipeline and board views
- record intake queue
- activity timeline
- task/calendar view
- filter builder
- outreach surfaces
- settings and governance
- fast search and drill-down
- approval surfaces when human review is required

### 12) Intelligence, credits, and market surfaces

Ares must surface market intelligence and cost awareness without becoming a data swamp.

Must include:

- skip tracing / enrichment requests
- credit usage and ledger
- market / prospecting surfaces
- sold-property and neighborhood context where useful
- reactivation queues
- lead scoring and prioritization
- dashboard summaries for what needs human attention now

## File-path map

This is the scope map for where the work belongs in the repo.

### Current backend surfaces to extend

- `app/main.py`
- `app/api/mission_control.py`
- `app/api/lead_machine.py`
- `app/api/marketing.py`
- `app/api/rbac.py`
- `app/api/permissions.py`
- `app/api/usage.py`
- `app/api/approvals.py`
- `app/api/audit.py`
- `app/api/trigger_callbacks.py`
- `app/api/outcomes.py`
- `app/api/sessions.py`
- `app/api/skills.py`
- `app/models/mission_control.py`
- `app/models/contacts.py`
- `app/models/leads.py`
- `app/models/opportunities.py`
- `app/models/tasks.py`
- `app/models/campaigns.py`
- `app/models/messages.py`
- `app/models/conversations.py`
- `app/models/lead_events.py`
- `app/models/marketing_leads.py`
- `app/models/outcomes.py`
- `app/models/rbac.py`
- `app/models/permissions.py`
- `app/models/audit.py`
- `app/models/approvals.py`
- `app/models/usage.py`
- `app/models/sequences.py`
- `app/models/bookings.py`
- `app/services/opportunity_service.py`
- `app/services/lead_task_service.py`
- `app/services/lead_sequence_runner.py`
- `app/services/lead_outbound_service.py`
- `app/services/inbound_sms_service.py`
- `app/services/lead_webhook_service.py`
- `app/services/lead_suppression_service.py`
- `app/services/marketing_lead_service.py`
- `app/services/campaign_lifecycle_service.py`
- `app/services/mission_control_service.py`
- `app/services/audit_service.py`
- `app/services/approval_service.py`
- `app/services/rbac_service.py`
- `app/services/permission_service.py`
- `app/services/provider_registry_service.py`
- `app/services/provider_preflight_service.py`
- `app/services/provider_retry_service.py`
- `app/services/provider_extras_service.py`
- `app/services/run_lifecycle_service.py`
- `app/services/booking_service.py`
- `app/services/outcome_service.py`
- `app/services/hermes_tools_service.py`
- `app/providers/textgrid.py`
- `app/providers/resend.py`
- `app/providers/instantly.py`
- `app/providers/calcom.py`

### Current persistence surfaces to extend

- `app/db/client.py`
- `app/db/contacts.py`
- `app/db/leads.py`
- `app/db/opportunities.py`
- `app/db/tasks.py`
- `app/db/campaigns.py`
- `app/db/messages.py`
- `app/db/conversations.py`
- `app/db/lead_events.py`
- `app/db/events.py`
- `app/db/automation_runs.py`
- `app/db/audit.py`
- `app/db/approvals.py`
- `app/db/rbac.py`
- `app/db/permissions.py`
- `app/db/usage.py`
- `app/db/sequences.py`
- `app/db/permissions.py`
- `app/db/provider_webhooks.py`
- `app/db/artifacts.py`
- `app/db/lead_machine_supabase.py`
- `app/db/marketing_supabase.py`

### Frontend cockpit surfaces to extend

- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/main.tsx`
- `apps/mission-control/src/components/MissionControlShell.tsx`
- `apps/mission-control/src/components/InboxList.tsx`
- `apps/mission-control/src/components/DashboardSummary.tsx`
- `apps/mission-control/src/components/ContextPanel.tsx`
- `apps/mission-control/src/components/RunTimeline.tsx`
- `apps/mission-control/src/components/TurnTimeline.tsx`
- `apps/mission-control/src/components/ConversationThread.tsx`
- `apps/mission-control/src/components/ApprovalQueue.tsx`
- `apps/mission-control/src/components/AgentRegistryTable.tsx`
- `apps/mission-control/src/pages/DashboardPage.tsx`
- `apps/mission-control/src/pages/InboxPage.tsx`
- `apps/mission-control/src/pages/IntakePage.tsx`
- `apps/mission-control/src/pages/PipelinePage.tsx`
- `apps/mission-control/src/pages/TasksPage.tsx`
- `apps/mission-control/src/pages/TurnsPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`
- `apps/mission-control/src/pages/SettingsPage.tsx`
- `apps/mission-control/src/pages/ApprovalsPage.tsx`
- `apps/mission-control/src/pages/AgentsPage.tsx`

### Proposed new surfaces if the current files get too crowded

- `app/api/contacts.py`
- `app/api/properties.py`
- `app/api/companies.py`
- `app/api/opportunities.py`
- `app/api/pipelines.py`
- `app/api/boards.py`
- `app/api/activities.py`
- `app/api/communications.py`
- `app/api/imports.py`
- `app/api/exports.py`
- `app/api/files.py`
- `app/api/webhooks.py`
- `app/api/workflows.py`
- `app/api/integrations.py`
- `app/api/mcp.py`
- `apps/mission-control/src/pages/ContactsPage.tsx`
- `apps/mission-control/src/pages/PropertiesPage.tsx`
- `apps/mission-control/src/pages/OpportunitiesPage.tsx`
- `apps/mission-control/src/pages/RecordsPage.tsx`
- `apps/mission-control/src/pages/ActivityPage.tsx`

## Task-by-task scope

These are work packages, not a tiny implementation checklist. Each one is a real slice of the product.

### Task 1: Tenant, auth, and permission foundation

**Purpose:** lock down workspace boundaries and access policy before anything else leaks data.

**Files:**
- `app/models/rbac.py`
- `app/models/permissions.py`
- `app/services/rbac_service.py`
- `app/services/permission_service.py`
- `app/db/rbac.py`
- `app/db/permissions.py`
- `app/api/rbac.py`
- `app/api/permissions.py`
- `app/api/mission_control.py`

**Scope:**
- workspace-aware identities
- roles and permission checks
- machine credentials / API keys
- audit events for access changes
- visibility rules for records, tasks, and timelines

**Done when:**
- all CRM reads and writes are workspace-scoped
- the UI only shows objects the user can actually touch
- integrations can be authenticated without becoming full users

### Task 2: Canonical CRM objects and relationship graph

**Purpose:** create the source of truth for people, properties, companies, records, and opportunities.

**Files:**
- `app/models/contacts.py`
- `app/models/leads.py`
- `app/models/opportunities.py`
- `app/models/campaigns.py`
- `app/models/marketing_leads.py`
- `app/models/messages.py`
- `app/models/conversations.py`
- `app/db/contacts.py`
- `app/db/leads.py`
- `app/db/opportunities.py`
- `app/db/campaigns.py`
- `app/db/marketing_supabase.py`
- `app/db/lead_machine_supabase.py`
- `app/services/opportunity_service.py`
- `app/services/marketing_lead_service.py`

**Scope:**
- identity resolution
- owner/contact/property linking
- custom fields
- canonical record graph
- merge/dedupe safety
- timeline-friendly object IDs

**Done when:**
- a lead can be traced from raw intake to canonical entity to opportunity
- merges preserve history instead of nuking it

### Task 3: Pipelines, stages, boards, and opportunity movement

**Purpose:** give Ares a real CRM state machine, not just a list of contacts.

**Files:**
- `app/models/opportunities.py`
- `app/models/sequences.py`
- `app/services/opportunity_service.py`
- `app/services/campaign_lifecycle_service.py`
- `app/api/lead_machine.py`
- `app/api/mission_control.py`
- `app/api/approvals.py`
- `apps/mission-control/src/pages/PipelinePage.tsx`
- `apps/mission-control/src/components/MissionControlShell.tsx`

**Scope:**
- pipelines and stages
- board phases / columns
- stage movement
- hidden / archived stage handling
- won / lost / abandoned / nurture states
- stage history
- operator-visible reasons for closure

**Done when:**
- pipeline movement is auditable and reversible
- board state and CRM state do not fight each other like toddlers in a car seat

### Task 4: Activity timeline, communications, and dispositions

**Purpose:** make every channel event land in one normalized history stream.

**Files:**
- `app/models/lead_events.py`
- `app/models/messages.py`
- `app/models/conversations.py`
- `app/models/outcomes.py`
- `app/services/audit_service.py`
- `app/services/inbound_sms_service.py`
- `app/services/lead_outbound_service.py`
- `app/services/outcome_service.py`
- `app/db/lead_events.py`
- `app/db/messages.py`
- `app/db/conversations.py`
- `app/db/outcomes.py`
- `app/api/mission_control.py`

**Scope:**
- immutable event history
- call / SMS / mail / email history
- dispositions and number health
- attempt counts
- timeline filters
- bulk job visibility

**Done when:**
- any lead can be opened and understood from the activity stream alone

### Task 5: Tasks, notes, assignments, and calendars

**Purpose:** unify operator work across the whole CRM.

**Files:**
- `app/models/tasks.py`
- `app/models/bookings.py`
- `app/services/lead_task_service.py`
- `app/services/booking_service.py`
- `app/services/mission_control_service.py`
- `app/db/tasks.py`
- `app/db/bookings.py`
- `app/api/mission_control.py`
- `apps/mission-control/src/pages/TasksPage.tsx`
- `apps/mission-control/src/pages/TurnsPage.tsx`

**Scope:**
- tasks on contacts, properties, opportunities, and records
- recurring tasks
- assignment rules
- reminders
- calendar linkage
- notes and operator memory

**Done when:**
- the same task model powers the whole product instead of three disconnected checklists

### Task 6: Segmentation, filters, tags, lists, and saved views

**Purpose:** turn filtering into a power tool, not an admin afterthought.

**Files:**
- `app/models/contacts.py`
- `app/models/leads.py`
- `app/models/marketing_leads.py`
- `app/services/marketing_lead_service.py`
- `app/api/marketing.py`
- `app/api/mission_control.py`
- `apps/mission-control/src/pages/IntakePage.tsx`
- `apps/mission-control/src/pages/DashboardPage.tsx`

**Scope:**
- tags
- lists
- statuses
- presets
- any/all filter logic
- attempt-count filters
- custom field filtering
- segment reuse across views and campaigns

**Done when:**
- every operator can save the exact lead slice they want and come back to it later

### Task 7: Imports, exports, files, dedupe, and merge

**Purpose:** make Ares portable and safe to ingest data into.

**Files:**
- `app/models/marketing_leads.py`
- `app/models/agent_assets.py`
- `app/services/lead_webhook_service.py`
- `app/services/provider_extras_service.py`
- `app/db/artifacts.py`
- `app/db/provider_webhooks.py`
- `app/api/marketing.py`
- `app/api/mission_control.py`
- `app/api/usage.py`

**Scope:**
- file upload
- field mapping
- add vs update imports
- export jobs
- attachment handling
- dedupe and merge safety
- schema discovery
- portability without vendor lock-in

**Done when:**
- the system can import a messy file, map it, dedupe it, and export it back out cleanly

### Task 8: Outreach, attempt tracking, and provider adapters

**Purpose:** let Ares actually contact people without losing state.

**Files:**
- `app/providers/textgrid.py`
- `app/providers/resend.py`
- `app/providers/instantly.py`
- `app/providers/calcom.py`
- `app/services/inbound_sms_service.py`
- `app/services/lead_outbound_service.py`
- `app/services/lead_sequence_runner.py`
- `app/services/lead_suppression_service.py`
- `app/models/messages.py`
- `app/models/conversations.py`
- `app/models/outcomes.py`
- `app/api/lead_machine.py`

**Scope:**
- SMS
- dialer events
- direct mail queueing
- email where relevant
- attempt counters per lead and number
- call statuses and dispositions
- contactability suppression rules
- provider response normalization

**Done when:**
- every outreach attempt shows up in the same CRM history and changes the right state

### Task 9: Workflows, sequences, webhooks, and MCP

**Purpose:** make the system reactive and agent-friendly.

**Files:**
- `app/services/lead_sequence_runner.py`
- `app/services/lead_webhook_service.py`
- `app/services/campaign_lifecycle_service.py`
- `app/services/provider_registry_service.py`
- `app/services/provider_preflight_service.py`
- `app/services/provider_retry_service.py`
- `app/api/trigger_callbacks.py`
- `app/api/webhooks.py`
- `app/api/mcp.py`
- `app/api/approvals.py`

**Scope:**
- event triggers
- stage-change triggers
- stale-lead triggers
- sequence enrollment / exit
- replay-safe actions
- durable webhooks
- schema/tool exposure for agents
- approval gates where automation needs a human

**Done when:**
- state changes can cause reliable work without hand-holding every time

### Task 10: Mission Control cockpit UI

**Purpose:** present the operator view that actually makes this usable.

**Files:**
- `apps/mission-control/src/App.tsx`
- `apps/mission-control/src/main.tsx`
- `apps/mission-control/src/components/MissionControlShell.tsx`
- `apps/mission-control/src/components/InboxList.tsx`
- `apps/mission-control/src/components/DashboardSummary.tsx`
- `apps/mission-control/src/components/ContextPanel.tsx`
- `apps/mission-control/src/components/RunTimeline.tsx`
- `apps/mission-control/src/components/TurnTimeline.tsx`
- `apps/mission-control/src/components/ConversationThread.tsx`
- `apps/mission-control/src/components/ApprovalQueue.tsx`
- `apps/mission-control/src/pages/DashboardPage.tsx`
- `apps/mission-control/src/pages/InboxPage.tsx`
- `apps/mission-control/src/pages/IntakePage.tsx`
- `apps/mission-control/src/pages/PipelinePage.tsx`
- `apps/mission-control/src/pages/TasksPage.tsx`
- `apps/mission-control/src/pages/TurnsPage.tsx`
- `apps/mission-control/src/pages/RunsPage.tsx`
- `apps/mission-control/src/pages/SettingsPage.tsx`
- `apps/mission-control/src/pages/ApprovalsPage.tsx`
- `apps/mission-control/src/pages/AgentsPage.tsx`

**Scope:**
- unified profile views
- pipeline and board surfaces
- intake queue
- activity/timeline pages
- task surfaces
- settings and governance
- approvals
- fast search and drill-down

**Done when:**
- the operator can run the machine from one cockpit instead of seven tabs and a prayer

### Task 11: Intelligence, credits, and market context

**Purpose:** add the real-estate intelligence layer without turning the app into a junk drawer.

**Files:**
- `app/services/probate_hcad_match_service.py`
- `app/services/probate_lead_bridge_service.py`
- `app/services/probate_lead_score_service.py`
- `app/services/probate_write_path_service.py`
- `app/services/harris_probate_intake_service.py`
- `app/models/usage.py`
- `app/models/marketing_leads.py`
- `app/api/usage.py`
- `app/api/marketing.py`
- `apps/mission-control/src/pages/DashboardPage.tsx`

**Scope:**
- enrichment and skip trace usage
- credits and cost awareness
- lead scoring
- market / sold-property context
- reactivation queues
- dashboard prioritization for what deserves human attention now

**Done when:**
- Ares knows what to chase, what to suppress, and what is worth a human calling

### Task 12: Governance, audit, and hardening

**Purpose:** keep the thing trustworthy once it starts doing real work.

**Files:**
- `app/models/audit.py`
- `app/models/approvals.py`
- `app/models/usage.py`
- `app/services/audit_service.py`
- `app/services/approval_service.py`
- `app/services/run_lifecycle_service.py`
- `app/services/provider_retry_service.py`
- `app/services/provider_preflight_service.py`
- `app/services/provider_registry_service.py`
- `app/api/audit.py`
- `app/api/approvals.py`
- `app/api/usage.py`

**Scope:**
- immutable audit logs
- approval history
- retries and failure handling
- provider health checks
- permissioned operational actions
- traceability for automation

**Done when:**
- the system can explain what happened, who did it, and why without hand-waving

## Non-goals

- Do not clone HighLevel or REISift UI verbatim.
- Do not collapse all statuses into one enum.
- Do not make notes a dumping ground for structured data.
- Do not let a vendor CRM become the source of truth.
- Do not build channels without a normalized event model.
- Do not ship a pretty dashboard before the operator model is real.
- Do not hide audit and ownership behavior behind magic.

## Delivery standard

Ares is complete only when all of these are true:

1. workspace-scoped data ownership exists
2. canonical CRM entities are stable
3. pipeline/stage/opportunity movement is real
4. task and note surfaces are unified
5. activity and communication history are normalized
6. segmentation is first-class
7. imports/exports are safe
8. outreach channels are integrated
9. workflows and sequences are reliable
10. webhooks/MCP/integrations are durable
11. the Mission Control cockpit makes the system usable
12. audit, governance, and credits are visible

## Source notes

This master scope is backed by the working synthesis artifacts in the repo and research wiki.

- `/root/wiki/queries/ares-backend-crm-primitives-synthesis.md`
- `/root/wiki/comparisons/highlevel-vs-reisift-vs-nakatomi-for-ares.md`
- `/root/wiki/concepts/highlevel-crm-primitives.md`
- `/root/wiki/concepts/reisift-lead-management-principles.md`
- `/root/wiki/concepts/reisift-upload-intake-and-mapping.md`
- `/root/wiki/concepts/reisift-sequences-and-board-automation.md`
- `/root/wiki/concepts/reisift-direct-mail-and-multitouch.md`
- `/root/wiki/concepts/reisift-integrations-sms-dialers.md`
- `/root/wiki/concepts/reisift-bulk-actions-and-activity-tracking.md`
- `/root/wiki/concepts/reisift-siftmap-prospecting-and-comps.md`
- `/root/wiki/concepts/reisift-data-management-reengagement-and-return-mail.md`

## Bottom line

Ares is not a CRM wrapper. It is the self-hosted operating system for lead management.

Own the data. Automate the work. Surface only the decisions that need a human.
