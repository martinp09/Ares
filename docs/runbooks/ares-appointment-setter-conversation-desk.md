# Ares Appointment Setter Conversation Desk Runbook

## Purpose

This runbook turns the Appointment Setter from a human-sounding SMS draft layer into a controlled acquisitions ISA workflow. It also defines how Chatwoot-style conversation tracking should be adapted inside Ares Mission Control.

## Current safe posture

- TextGrid inbound/outbound plumbing exists.
- SMS reply-agent decisions are stored/audited.
- Global live seller auto-replies remain disabled unless runtime gates are explicitly enabled.
- Appointment Setter is least-privilege: it receives sanitized conversation packets and returns structured decisions; Ares owns all sends, Slack posts, calendar actions, and kill switches.

## Core operating rule

> Appointment Setter can qualify and draft. Ares validates and acts. Martin can take over immediately.

## Conversation stages

1. Property identity.
2. Authority / relationship to owner.
3. Motivation / why now.
4. Timeline.
5. Condition / occupancy.
6. Price / desired outcome.
7. Route: appointment, Martin review, nurture, research, disqualify, or stop.

Ask one clear question per SMS unless answering a direct seller question.

## Qualification buckets

- `hot`: high motivation, authority/path to authority, near timeline, real property.
- `appointment_ready`: hot plus seller is ready/willing to talk or asks for a call.
- `warm`: real but missing details or timeline softer.
- `needs_research`: missing property/owner/title/tax/contact facts.
- `needs_human_review`: legal/title/probate ambiguity, seller asks for Martin, hard curveball.
- `long_nurture`: real but not ready; recommend follow-up, do not enroll automatically.
- `disqualified`: STOP, DNC/suppression, wrong number, no owner path, outside buy-box, hostile/legal threat.

## Kill switch procedure

Ares should check these before every Appointment Setter LLM call and again before any SMS send or booking:

1. Global: `APPOINTMENT_SETTER_ENABLED=false` or equivalent runtime flag.
2. Channel/source pause: provider/source route disabled.
3. Conversation: `manual_control=true` / `appointment_setter_paused=true`.

When Martin takes over:

- stop auto replies immediately;
- continue mirroring inbound texts to Slack/Mission Control;
- mark thread owner as `martin`;
- require explicit resume before Appointment Setter can draft/send again.

## Slack route

Recommended route/env:

- route: `appointment_setter`
- env: `SLACK_CHANNEL_APPOINTMENT_SETTER`
- feature gate: `APPOINTMENT_SETTER_SLACK_ENABLED=false` by default

Slack posts should include:

- bucket and score
- sanitized seller summary
- exact next action
- whether auto-send was blocked
- buttons/commands for Take Over, Approve Reply, Edit, Nurture, Disqualify, Book/Hold Appointment

Avoid raw PII/contact dumps in Slack.

## Calendar route

Calendar remains Ares-owned.

Allowed future flow:

1. Appointment Setter detects appointment intent and preferred window.
2. Ares checks Cal.com/Google free-busy with least privilege.
3. Ares returns safe slot labels only.
4. Appointment Setter asks seller to choose a slot or recommends Martin approval.
5. Ares books/holds only Ares-created appointments under approved policy.

Private calendar event details must never go to the LLM.

## Chatwoot patterns to adapt

Use Chatwoot as a pattern source for:

- inbox list + selected thread
- conversation statuses
- assignment / bot-vs-human owner
- labels/custom attributes
- private notes
- macros/canned responses
- automation rules
- agent-bot handoff
- reporting and response metrics

Do not adopt Chatwoot as the canonical source of truth by default. Ares remains canonical.

## Production activation gates

Before any seller-facing live auto-reply:

- offline simulator passes;
- owned-number smoke passes;
- prompt-injection suite passes;
- STOP/DNC/suppression tests pass;
- manual takeover works;
- max-turn and expiry gates work;
- Slack human-review route is ready;
- TextGrid final provider status polling works;
- Martin approves exact source/channel/receiver scope.

## What remains manual

- Seller calls.
- Offer decisions.
- Legal/title judgments.
- Paid skiptrace beyond explicit approval.
- Campaign activation/enrollment.
- Broad calendar booking policy changes.
