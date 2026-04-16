---
title: "Ares Lead Machine Superfile 2026"
status: active
updated_at: "2026-04-16T16:41:59Z"
source_notes:
  - "Hermes — Instantly Lead Automation Final Spec 2026"
  - "2026-04-16 Harris County Probate Keep-Now Ingestion Implementation Plan"
  - "2026-04-16 Curative Title Cold Email Machine Implementation Plan"
---

# Ares Lead Machine Superfile 2026

This is the single live doc for the lead machine.
If an older note disagrees with this file, this file wins.

Primary emphasis: Harris County probate keep-now ingestion.
Overall goal: build the whole lead machine end-to-end, from source intake to scored lead to outbound sequencing to operator follow-up, without confusing any provider for the source of truth.

## What this machine is

Ares owns the brain.
Providers own transport.
Mission Control owns the operator cockpit.
Trigger.dev owns async orchestration.

The machine has one canonical loop:
1. find or ingest a lead
2. normalize it
3. score it
4. route it
5. send the right outbound touch, if any
6. ingest provider webhooks
7. create the right manual task only after confirmed delivery
8. keep suppression, audit, and operator state in Ares

## Hard boundaries

- Ares/Hermes is the source of truth.
- Instantly/Smartlead are cold outbound transport only.
- Resend is for transactional / opt-in / nurture only.
- Trigger.dev handles retries, schedules, webhook fan-in, and background jobs.
- Mission Control is the operator surface.
- Do not build a second CRM.
- Do not store task state inside providers.
- Do not create manual call tasks on queued, requested, attempted, or failed sends.
- Do not wire live Supabase/backend persistence until the fixture-backed slice is validated.

## Canonical data model

Use one shared canonical model for the machine, then project lane-specific views from it.

### leads
Canonical lead record.
Core fields:
- id
- full_name
- first_name
- last_name
- email
- phone
- address
- source
- score
- status
- suppression_state
- created_at
- updated_at

### lead_events
Append-only event log for everything meaningful.
Core fields:
- id
- lead_id
- event_type
- provider
- provider_event_id
- campaign_id
- automation_run_id
- source_event_id
- payload_json
- created_at

Important event types:
- lead.created
- lead.scored
- lead.routed
- email.requested
- email.sent
- email.failed
- reply.received
- bounce.received
- unsubscribed
- task.created
- task.completed
- lead.suppressed

### automation_runs
One row per workflow execution path.
Core fields:
- id
- lead_id
- campaign_id
- current_step
- status
- idempotency_key
- started_at
- finished_at
- last_error

### campaign_memberships
Maps a lead to an outbound campaign.
Core fields:
- id
- lead_id
- campaign_id
- provider_campaign_id
- status
- added_at
- last_sync_at

### tasks
Manual work queue for operators.
Core fields:
- id
- lead_id
- automation_run_id
- source_event_id
- task_type
- status
- priority
- due_at
- assigned_to
- title
- notes
- created_at
- completed_at
- idempotency_key

Recommended task types:
- call_followup
- voicemail_followup
- manual_review
- exception
- callback
- reply_needed

Recommended task statuses:
- open
- assigned
- in_progress
- done
- snoozed
- cancelled
- failed

## Priority order

This is the build order.

### 1) Harris County probate keep-now ingestion
Primary lane.
This is the lead source that matters most.

### 2) HCAD enrichment and scoring
Still part of the primary lane.
This is what turns a boring filing into an actual lead.

### 3) Curative title cold email machine
Outbound execution lane.
This is how the machine moves keep-now leads into actual contact.

### 4) Mission Control operator views
Fixture-backed first, live later.

### 5) Live backend wiring
Only after the fixture contracts and local scripts are proving the loop.

## Lane 1: Harris County probate keep-now ingestion

This lane exists to pull Harris County probate filings, keep the high-alpha categories, normalize them, score them, and surface them in Mission Control.

### Keep-now categories
Only retain these in the first slice:
- Probate of Will (Independent Administration)
- Independent Administration
- App for Independent Administration with Will Annexed
- App for Independent Administration with an Heirship
- App to Determine Heirship

Do not prioritize yet:
- Dependent Administration
- Small Estate
- Guardianship
- Miscellaneous probate buckets
- Ancillary Administration
- Muniment of Title hidden inside broad buckets

### Probate intake data shape
Normalized probate lead record should include:
- case_number
- file_date
- court_number
- status
- filing_type
- filing_subtype
- estate_name
- decedent_name
- source = harris_county_probate
- keep_now = true/false
- hcad_match_status
- hcad_acct
- owner_name
- mailing_address
- contact_confidence
- lead_score
- outreach_status
- last_seen_at

### Primary workflow
1. Pull probate filings by file-date range.
2. Save raw rows for traceability.
3. Normalize filings into the stable lead shape.
4. Apply the keep-now filter immediately.
5. Match against HCAD when possible.
6. Score the lead deterministically.
7. Surface the result in Mission Control.

### HCAD matching rules
- normalize estate names
- try owner-name matching first
- try decedent-name matching second
- preserve the padded-account trim rule already known in HCAD_Query
- never invent a match
- mark unmatched records explicitly

### Scoring rules
High priority:
- Probate of Will (Independent Administration)
- Independent Administration
- App for Independent Administration with Will Annexed
- App for Independent Administration with an Heirship
- App to Determine Heirship

Score down for:
- no HCAD match
- no mailing address
- ambiguous estate naming
- multiple likely property candidates

### Probate operator views
Mission Control should show:
- today’s probate count
- keep-now count
- matched vs unmatched
- top-scored leads
- filter chips for the keep-now categories
- timeline for a selected lead
- exception state when a filing is noisy or malformed

### Probate exit gate
Do not wire live backend storage until:
- the keep-now filter is stable
- HCAD matching works on fixture data
- Mission Control renders the lead queue correctly
- the cron cadence and handoff rules are documented

## Lane 2: Curative title cold email machine

This is the outbound execution arm.
It uses the same canonical lead machine, but it is not the source of truth.

### Provider policy
Use the right hammer for the job:
- Instantly / Smartlead: cold outbound, inbox rotation, warm-up, sequencing, deliverability tooling
- Resend: transactional mail, opt-in nurture, confirmations, internal notifications

Ares owns:
- campaign selection
- lead routing
- suppression
- task creation
- operator state
- audit history

Providers own:
- sending
- provider-side sequencing
- provider event delivery

### Campaign state model
- draft
- ready
- warming
- sending
- paused
- bounced
- replied
- suppressed
- exhausted
- failed

### Safety dimensions
- consent_status
- unsubscribe_status
- bounce_status
- mailbox_health
- domain_health
- lead_source
- sequence_step
- last_touch_at

### State flow
Normal path:
1. lead.created
2. lead.scored
3. lead.routed
4. email.requested
5. provider accepts the lead into the campaign
6. email.sent arrives back via webhook
7. Hermes creates one manual call task
8. operator completes the call task
9. next step runner decides whether to send the next touch, suppress, or close out

Exception paths:
- email.failed -> exception task, not call_followup
- reply.received -> pause or stop automation
- bounce.received -> suppress lead
- unsubscribed -> suppress lead
- do-not-contact -> suppress lead

### Rules that must not move
- email.sent is the only event that can spawn the manual call task.
- email.queued does not spawn the task.
- email.requested does not spawn the task.
- email.failed does not spawn the task.
- one send event = one call task maximum.
- any reply, bounce, unsubscribe, or do-not-contact event overrides the automation.
- every retry path must be idempotent.
- Instantly is not the source of truth.
- Resend is not the cold outbound sequencer.

### Suppression rules
Stop sends for:
- replies
- unsubscribes
- hard bounces
- invalid mailbox states
- known bad domains
- duplicate leads already in an active sequence

### Curative-title outreach behavior
- probate keep-now lead -> cold outbound sequence
- website form lead -> transactional or nurture flow, not cold outbound
- hot replied lead -> stop sequence and hand to operator inbox

### Cold outbound operator views
Mission Control should show:
- active campaigns
- mailbox health
- send counts
- reply counts
- suppressed leads
- nurture vs cold routing
- exceptions
- the next action

### Cold email exit gate
Do not connect live provider credentials or backend dispatch until:
- the provider policy is stable
- suppression rules are proven
- Mission Control renders the outreach state correctly
- the cold-email machine is clearly separated from transactional Resend usage

## Shared jobs / orchestration

### lead-intake
Input:
- raw lead submission or normalized intake record

Responsibilities:
- normalize the lead
- dedupe it
- score it
- create or update the lead row
- write lead.created / lead.scored / lead.routed events
- create or update automation_runs
- decide whether the lead should be sent onward

Output:
- lead_id
- campaign_id
- should_dispatch

### instantly-enqueue-lead
Input:
- lead_id
- campaign_id
- normalized contact payload

Responsibilities:
- add the lead to the chosen outbound campaign/list
- write email.requested
- let the provider own the actual sending and sequencing

### instantly-webhook-ingest
Input:
- provider webhook payload

Responsibilities:
- verify the webhook
- map provider event to internal event_type
- write lead_events
- update lead status / suppression as needed
- treat webhook replay as idempotent

### create-manual-call-task
Input:
- confirmed email.sent event

Responsibilities:
- create exactly one call_followup task
- use source_event_id or email_event_id as the idempotency anchor
- write task.created

### followup-step-runner
Input:
- task completion or reply / suppression state

Responsibilities:
- decide next touch
- send the next email if appropriate
- schedule the next step if appropriate
- stop the flow if the lead is suppressed

### suppression-sync
Input:
- reply, bounce, unsubscribe, or do-not-contact state

Responsibilities:
- update suppression flags
- prevent future sends
- ensure future campaign adds are blocked

### task-reminder-or-overdue
Input:
- due task state

Responsibilities:
- nudge the operator
- escalate overdue tasks
- resurface stalled manual work

## Mission Control requirements

Mission Control should show:
- the probate queue
- the outreach queue
- the lead record
- the automation run status
- the latest provider event
- the manual call task queue
- suppression state
- next action
- exception state
- audit and usage surfaces

The operator must be able to:
- see the call task
- complete the call task
- add call notes
- mark follow-up outcomes
- pause or suppress the lead when needed

## Build order

If you are implementing this from scratch, do it in this order:

1. Harris County probate puller + keep-now filter
2. HCAD matching + lead scoring
3. provider contract + suppression state machine
4. outbound enqueue / webhook ingest / task creation jobs
5. Mission Control fixture views
6. docs / TODO / memory / handoff cleanup

## Verification criteria

The system is correct only if all of these are true:

- a duplicate lead submission does not create duplicate runs or duplicate call tasks
- a webhook replay does not create duplicate events or tasks
- email.sent creates exactly one manual call task
- email.failed creates an exception, not a call task
- reply.received suppresses future sends
- bounce.received suppresses future sends
- unsubscribed suppresses future sends
- operator completion of a task can advance the next step cleanly
- the probate lane still prioritizes keep-now categories first

## Implementation pointer

This file is the live source of truth.
The older plan/spec docs are folded into this superfile and should be treated as source notes, not separate live TODO items.

## Related source notes

- Hermes — Instantly Lead Automation Final Spec 2026
- 2026-04-16 Harris County Probate Keep-Now Ingestion Implementation Plan
- 2026-04-16 Curative Title Cold Email Machine Implementation Plan
