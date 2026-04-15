# Lease-Option Marketing MVP Design

> Live marketing MVP for Ares. FastAPI remains the backend. Trigger.dev runs delayed automation. Supabase is the canonical target for lead, conversation, task, and booking state. `Cal.com`, `TextGrid`, and `Resend` are provider layers only.

## Goal

Ship a live lease-option marketing MVP that captures seller leads from the landing page, tracks submitted-but-not-booked sellers, sends immediate SMS and email confirmations, enrolls non-bookers into a 10-day SMS-intensive campaign after 5 minutes, creates internal manual-call tasks, and handles inbound SMS qualification and booking-state changes inside Hermes.

The first target avatar is homeowners with listings at `45+ days on market`. Voice is out of scope.

## Architecture Summary

Ares owns lead state, booking state, conversation state, sequence state, task state, approvals, and operator visibility. The landing page should hand form submissions to Hermes instead of `n8n`. `Cal.com` remains the booking source of truth. `TextGrid` remains the SMS transport. `Resend` handles transactional email and light check-ins. Trigger.dev handles the five-minute booking check, the delayed SMS sequence, and internal follow-up timing. Supabase is the long-term canonical store and already has baseline tables for `contacts`, `conversations`, and `tasks`.

Implementation status at design time:
- Hermes already has command, run, approval, artifact, and Mission Control scaffolding.
- Hermes does not yet own marketing lead intake, booking webhooks, SMS/email sending, sequence enrollment, or inbound SMS qualification.
- The landing page at `/Users/solomartin/Business/website/lease-options-landing` already persists form submissions, builds a `Cal.com` URL with `lead_id`, and currently dispatches to `n8n`.
- A proven `TextGrid` adapter already exists in `/Users/solomartin/Projects/Phone System/api/_lib/providers/textgrid.js` and should be ported rather than redesigned.

## MVP Scope

### In Scope

1. Form-submit lead capture for the lease-option landing page.
2. Tracking sellers who submit the form but do not book.
3. Immediate confirmation on submit:
   - one SMS via `TextGrid`
   - one email via `Resend`
4. `Cal.com` booking webhook ingestion for:
   - booking created
   - booking rescheduled
   - booking cancelled
5. Appointment confirmation messaging:
   - booking confirmation SMS
   - booking confirmation email
6. A `5-minute non-booker check`.
7. A 10-day lease-option SMS campaign for sellers who submitted the form but did not book.
8. Internal manual-call tasks inserted at defined checkpoints in the 10-day campaign.
9. Inbound SMS and reply handling through `TextGrid` webhooks.
10. SMS qualification logic for lease-option sellers, including stop/pause/escalate behavior.
11. Mission Control visibility for lead status, booking status, sequence state, task state, and conversation activity.

### Out Of Scope

1. Voice and Vapi.
2. Anonymous visitor identity resolution.
3. A heavy email nurture campaign.
4. Broad real-estate use cases outside lease options.
5. A second scheduler or queue system outside Trigger.dev.
6. A provider switch away from `Cal.com`, `TextGrid`, or `Resend`.

## Product Rules

1. Form submitted and not booked means the lead is eligible for the campaign.
2. Booked leads must not enter the 10-day intensive.
3. Booking within 5 minutes suppresses campaign enrollment.
4. The 5-minute timer starts from successful form submission in Hermes.
5. Any inbound SMS reply must attach to the Hermes conversation for that lead.
6. Any opt-out or stop-style reply must pause or end SMS automation immediately.
7. The first campaign version is written only for lease-option sellers with `45+ DOM` messaging.
8. Hermes, not provider web UIs, is the source of truth for operator state.

## Core Objects

### Lead

Represents the seller record created from the landing page form.

Required MVP fields:
- contact identity
- property address
- seller timeline
- asking-price goal
- SMS consent metadata
- booking status
- campaign enrollment status
- qualification status

### Conversation

Represents the seller communication thread across SMS and light email. The Hermes baseline schema already includes `contacts` and `conversations`; this MVP adds message ownership and booking-aware state transitions around them.

### Booking State

Represents whether the lead is:
- `pending`
- `booked`
- `rescheduled`
- `cancelled`

### Sequence Enrollment

Represents whether the lead is:
- `not_enrolled`
- `active`
- `paused`
- `completed`
- `stopped`

### Internal Task

Represents manual follow-up work for operators, especially call tasks created when hot leads do not book or when replies need human intervention.

## System Responsibilities

### Landing Page

The landing page should:
- keep the current form UX
- submit the lead to Hermes instead of `n8n`
- redirect the seller to the personalized `Cal.com` booking URL Hermes returns

The redirect model is acceptable. A full `Cal.com` embed is not required for tracking submitted-but-not-booked sellers.

### Hermes Backend

Hermes should:
- accept the landing-page lead submission
- create or upsert the lead
- create the related conversation/contact state
- send immediate confirmation SMS and email
- schedule the five-minute booking check in Trigger.dev
- accept `Cal.com` booking webhooks
- update booking status
- enroll or suppress the 10-day campaign
- accept inbound `TextGrid` webhooks
- run qualification rules on replies
- create manual-call tasks
- expose read models to Mission Control

### Trigger.dev

Trigger.dev should:
- schedule the five-minute booking check
- run the 10-day SMS sequence
- schedule light email check-ins
- create timed internal task events
- retry safe provider calls

Trigger.dev should not own lead truth or booking truth.

### Providers

`Cal.com` owns booking execution only.

`TextGrid` owns SMS transport only.

`Resend` owns email delivery only.

## Flow Design

### Flow 1: Form Submit

1. Seller submits the lease-option landing-page form.
2. Hermes validates the payload and persists the lead as `booking_status = pending`.
3. Hermes creates or updates the contact and conversation.
4. Hermes sends:
   - submit confirmation SMS
   - submit confirmation email
5. Hermes returns the personalized `Cal.com` booking URL.
6. The landing page redirects the seller to `Cal.com`.
7. Hermes schedules a Trigger.dev job for `submitted_not_booked_check` at `+5 minutes`.

### Flow 2: Booking Created

1. `Cal.com` sends a booking webhook to Hermes.
2. Hermes resolves the lead using the `lead_id` or other booking context embedded in the scheduling URL.
3. Hermes sets `booking_status = booked`.
4. Hermes records the appointment event.
5. Hermes sends:
   - booking confirmation SMS
   - booking confirmation email
6. Hermes cancels or suppresses any pending non-booker campaign enrollment.

### Flow 3: Five-Minute Non-Booker Check

1. Trigger.dev wakes at `+5 minutes`.
2. Hermes checks whether the lead is still `booking_status = pending`.
3. If booked, the job exits cleanly.
4. If still pending, Hermes enrolls the lead in the 10-day intensive SMS sequence.
5. Hermes records campaign enrollment and schedules the remaining steps.

### Flow 4: 10-Day Intensive Campaign

The first version should be deliberately simple:
- SMS-heavy
- a few email check-ins
- manual call tasks at key points

Suggested pattern:
1. Day 0 after 5 minutes: first non-booker SMS.
2. Day 1: follow-up SMS.
3. Day 2: manual-call task.
4. Day 3: SMS.
5. Day 4: light email check-in.
6. Day 5: SMS.
7. Day 6: manual-call task.
8. Day 7: SMS.
9. Day 8: light email check-in.
10. Day 10: final SMS and campaign close.

Exact copy belongs in implementation, but the sequence must stay lease-option-specific and `45+ DOM`-aware.

### Flow 5: Inbound SMS Qualification

1. `TextGrid` sends inbound SMS or delivery/status webhooks to Hermes.
2. Hermes verifies the webhook and normalizes the event.
3. Hermes appends inbound content to the existing conversation.
4. Hermes runs qualification rules for:
   - seller intent
   - timeframe
   - openness to lease option
   - request to talk now
   - stop / unsubscribe intent
5. Hermes either:
   - auto-replies with the next approved qualification step
   - pauses automation and creates a manual-call task
   - stops the sequence
   - requests operator review for ambiguous replies

## Read Models For Mission Control

Mission Control should show, at minimum:
- new submitted leads
- pending vs booked appointments
- active 10-day campaign enrollments
- next scheduled step
- manual-call tasks due
- inbound replies needing review
- conversation history per lead

This is enough for an operator to know:
- who submitted
- who booked
- who needs follow-up
- who replied
- who needs a manual call

## Provider Decisions

### `Cal.com`

Keep it. It is already in the landing-page flow and is sufficient for the MVP. Hermes should consume booking webhooks and treat `Cal.com` as booking execution only.

### `TextGrid`

Keep it. The public `TextGrid` SMS docs position the API as Twilio-compatible, and a working adapter is already present in `Phone System`. Hermes should port that adapter and keep provider-specific assumptions isolated to the adapter layer.

### `Resend`

Keep it for immediate confirmations and occasional check-ins. Do not overbuild email orchestration in the first MVP.

## Data And Wiring Decisions

1. Hermes should replace the landing-page `n8n` webhook handoff for this flow.
2. The MVP should use the existing Hermes `.env` provider keys already present in this workspace.
3. Supabase should remain the canonical target for contacts, conversations, tasks, bookings, and sequence state.
4. If a temporary in-memory seam is needed to finish code paths today, it must be clearly isolated and replaced immediately after the live flow is proven.
5. No duplicate scheduler, no `n8n` dependency in the final MVP path, and no provider-specific state outside Hermes.

## Risks

1. The biggest risk is trying to finish both provider wiring and full Supabase persistence in one pass.
2. The second biggest risk is leaving `n8n` partially in the loop, which would split truth across systems.
3. The safest rollout is:
   - port the provider adapters
   - wire lead submit and booking events
   - wire the five-minute booking check
   - wire the SMS sequence and manual-call tasks
   - then expose the read model in Mission Control

## Acceptance Criteria

1. A seller submits the landing-page form and Hermes stores the lead as `pending`.
2. Hermes sends immediate SMS and email confirmation after submit.
3. The seller books through `Cal.com`, and Hermes marks them `booked`.
4. Hermes sends booking confirmation SMS and email.
5. A seller who does not book within 5 minutes is automatically enrolled in the 10-day intensive.
6. A booked seller is never enrolled in the intensive.
7. Inbound SMS replies appear in Hermes and can pause, stop, or escalate the sequence.
8. Manual-call tasks are created at defined sequence checkpoints.
9. Mission Control shows enough state for an operator to manage the flow without opening provider dashboards.
