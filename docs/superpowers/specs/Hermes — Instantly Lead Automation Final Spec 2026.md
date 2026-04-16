---
title: "Hermes — Instantly Lead Automation Final Spec 2026"
status: final
updated_at: "2026-04-16T04:33:30Z"
source_notes:
  - "Nick Saraev — Hermes TODOs 2026"
  - "Nick Saraev — What to Steal for Hermes 2026"
---

# Hermes — Instantly Lead Automation Final Spec 2026

This is the durable spec for the lead automation loop.

## Purpose

Build a real automation system where:
- Hermes/Ares is the source of truth
- Instantly handles cold outbound email sending and sequencing
- Trigger.dev handles orchestration, retries, schedules, and webhook fan-in
- Mission Control is the operator surface
- manual call follow-up tasks are created automatically after confirmed email delivery

The system should run like a loop, not like a pile of disconnected tricks.

## Non-goals

- Do not build a second CRM.
- Do not make Instantly the source of truth.
- Do not put task state inside Instantly.
- Do not create call tasks on queued or attempted sends.
- Do not merge SMS/calls into the email transport layer.
- Do not add extra orchestration layers unless they solve a real problem.

## Architecture boundary

Hermes/Ares owns:
- canonical lead state
- scoring and routing
- suppression and exclusions
- automation run state
- manual task creation and task state
- operator visibility
- audit trail and event history

Instantly owns:
- campaign CRUD
- lead add/move operations
- sequencing
- outbound email sending
- delivery/webhook events

Trigger.dev owns:
- async execution
- retries
- schedules
- webhook ingestion jobs
- follow-up job execution

Mission Control owns:
- inbox/task queue views
- lead timeline views
- exception handling views
- operator actions

## Data model

### 1) leads
Canonical lead row. One record per normalized lead.

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

### 2) lead_events
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

### 3) automation_runs
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

### 4) campaign_memberships
Maps a lead to an Instantly campaign.

Core fields:
- id
- lead_id
- campaign_id
- provider_campaign_id
- status
- added_at
- last_sync_at

### 5) tasks
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

## State flow

Normal path:
1. lead.created
2. lead.scored
3. lead.routed
4. email.requested
5. Instantly accepts the lead into the campaign
6. email.sent arrives back via webhook
7. Hermes creates one manual call task
8. operator completes the call task
9. next step runner decides whether to send the next touch, suppress, or close out

Exception paths:
- email.failed -> create exception event/task, not call_followup
- reply.received -> pause or stop automation
- bounce.received -> suppress lead
- unsubscribed -> suppress lead
- do-not-contact -> suppress lead

## Trigger.dev jobs

### lead-intake
Input:
- raw lead submission

Responsibilities:
- normalize the lead
- dedupe it
- score it
- create or update the lead row
- write lead.created / lead.scored / lead.routed events
- create or update automation_runs
- decide whether the lead should be sent to Instantly

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
- add the lead to the chosen Instantly campaign/list
- write email.requested
- let Instantly own the actual sending and sequencing

### instantly-webhook-ingest
Input:
- Instantly webhook payload

Responsibilities:
- verify the webhook
- map provider event to internal event_type
- write lead_events
- update lead status/suppression as needed
- treat webhook replay as idempotent

### create-manual-call-task
Input:
- confirmed email.sent event

Responsibilities:
- create exactly one call_followup task
- use source_event_id or email_event_id as the idempotency anchor
- write task.created

Rule:
- never create this task from queued, attempted, or requested send state

### followup-step-runner
Input:
- task completion or reply/suppression state

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

## Rules that must not move

- email.sent is the only event that can spawn the manual call task.
- email.queued does not spawn the task.
- email.requested does not spawn the task.
- email.failed does not spawn the task.
- one send event = one call task maximum.
- any reply, bounce, unsubscribe, or do-not-contact event overrides the automation.
- Instantly is not the source of truth.
- Hermes is the source of truth.
- every retry path must be idempotent.

## Idempotency rules

Use idempotency keys so retries do not create duplicates.

Suggested anchors:
- lead_id + campaign_id + campaign_step + provider_event_id
- lead_id + automation_run_id + source_event_id

At minimum:
- one automation run per unique lead/campaign path
- one task per confirmed send event
- one webhook event record per provider event id

## Mission Control requirements

Mission Control should show:
- the lead record
- the automation run status
- the latest provider event
- the manual call task queue
- suppression state
- next action
- exception state when something breaks

The operator must be able to:
- see the call task
- complete the call task
- add call notes
- mark follow-up outcomes
- pause or suppress the lead when needed

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

## Implementation pointer

This note is the final spec.

TODO.md should point here.
The old Nick Saraev checklist items are no longer live work and should stay out of the current todo list.

## Related notes

- [[TODO]]
- [[docs/superpowers/plans/2026-04-16-harris-probate-keep-now-ingestion-plan]]
- [[docs/superpowers/plans/2026-04-16-curative-title-cold-email-machine-plan]]
- [[Nick Saraev — What to Steal for Hermes 2026]]
- [[Nick Saraev — Hermes TODOs 2026]]
