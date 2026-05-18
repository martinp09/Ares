---
status: current
source_of_truth: true
superseded_by: null
last_verified: 2026-05-18
---

# Ares Appointment Setter + Conversation Desk Design

## Product thesis

Ares needs a first-step acquisitions employee over SMS: an Appointment Setter that qualifies, disqualifies, nurtures, escalates, and prepares appointment-ready seller conversations while Ares remains the only authority allowed to act.

This is not a generic support bot and not a closer. It is a real-estate ISA layer for the first acquisition conversation.

## Non-negotiable boundaries

Appointment Setter may think and draft. Ares acts.

Appointment Setter must not directly access:

- TextGrid, Slack, Cal.com, Google Calendar, Gmail, HubSpot, Instantly, skiptrace, Vapi, or any provider credential.
- terminal, filesystem, browser, GitHub, raw database credentials, all contacts, all leads, full private notes, or Hermes memory.
- live send, booking, campaign enrollment, paid enrichment, or CRM/provider mutation paths.

Ares owns:

- inbound TextGrid webhook handling
- contact/lead/property lookup
- STOP, DNC, suppression, wrong-number, legal/angry handling
- max-turns, business-hours, global/channel/conversation kill switches
- Slack escalation and manual takeover
- calendar/Cal.com/Google free-busy and appointment creation
- TextGrid sends
- audit logs and state transitions

## Chatwoot influence

Chatwoot is useful as a conversation-desk pattern library, not as the Ares source of truth. Ares should mine these concepts:

- inbox list and selected conversation thread
- contact profile side panel
- conversation status: open, pending, snoozed, resolved
- assignment: bot/human/team ownership
- labels/custom attributes
- private notes
- macros/canned responses
- automation rules
- agent-bot handoff webhooks
- SLA/response reporting

Ares should adapt those patterns into a real-estate acquisition desk rather than running a second generic support CRM by default.

## Conversation Desk layout

### Left queue

- Hot / appointment-ready
- Needs Martin
- Active SMS
- Needs research
- Long nurture
- Manual takeover
- Disqualified / dead
- STOP / DNC / wrong number

### Center thread

- inbound seller messages
- outbound Appointment Setter drafts/replies
- Martin manual replies
- delivery/provider status
- decision/audit markers

### Right context panel

- property card
- owner/contact card
- strategy lane
- qualification score
- authority / motivation / timeline / condition / price / occupancy
- blockers and missing evidence
- next best action
- current owner: Appointment Setter vs Martin
- manual takeover controls
- appointment/calendar controls
- nurture recommendation

## Qualification rubric

Total score: 100.

1. Property fit, 0-25
   - address/city known
   - target market
   - SFR 1-4 / buy-box fit
   - strategy lane known
   - condition/occupancy known enough

2. Authority, 0-20
   - owner
   - heir
   - spouse/family decision maker
   - authorized helper
   - can connect to decision maker
   - unclear probate/title authority lowers score and may force human review

3. Motivation/problem, 0-25
   - inherited property
   - delinquent taxes
   - vacancy
   - repairs
   - behind payments
   - tired landlord
   - family issue
   - title problem
   - wants options now

4. Timeline, 0-15
   - today / this week
   - this month
   - 30-90 days
   - later / exploring
   - no timeline

5. Contact/consent/readiness, 0-15
   - valid phone
   - okay texting
   - willing to talk
   - not suppressed/DNC
   - not wrong number
   - not hostile/legal threat

## Buckets

- `hot`: real property, authority/path to authority, motivation, near timeline, willing to talk, no channel block.
- `appointment_ready`: hot and asking for a call or accepted next step.
- `warm`: real property and some motivation, softer timeline or missing detail.
- `needs_research`: missing property/owner/title/tax/context before safe continuation.
- `needs_human_review`: title/probate/legal ambiguity, high-value lead, hard seller question, seller asks for Martin, confusing curveball.
- `long_nurture`: real but not ready; recommend SMS/email follow-up but do not auto-enroll without approval.
- `disqualified`: wrong number, no owner path, outside buy-box, no property, hostile/legal threat, STOP/DNC/suppressed.

## Multi-turn stages

1. `property_identity`: address/city/state and whether this is the property.
2. `authority`: owner/heir/decision maker/helper/path to decision maker.
3. `motivation`: why now.
4. `timeline`: now, this month, 30-90 days, later, exploring.
5. `condition_occupancy`: vacant/occupied/rented/repairs/inherited/title issue/access.
6. `price_outcome`: number in mind, cash/terms/options, no promises.
7. `route`: appointment-ready, Martin review, nurture, research, skiptrace/contact verification, disqualified, manual takeover.

## Manual takeover and kill switches

Ares must check kill switches before every LLM call and again before every send/booking.

Required switches:

- conversation takeover: `manual_control=true`, no auto replies, inbound mirrors to Slack/Mission Control.
- channel/source pause: stop Appointment Setter for a provider/source route.
- global pause: `APPOINTMENT_SETTER_ENABLED=false` or equivalent runtime config.

Mission Control and Slack should expose fast actions:

- Take Over Thread
- Pause Appointment Setter
- Resume Appointment Setter
- Approve Reply
- Edit Reply
- Disqualify
- Send to Nurture
- Request Calendar Slots
- Book/Hold Appointment

## Calendar contract

Appointment Setter can request calendar actions only via structured output:

```json
{
  "calendar_action_requested": true,
  "next_best_action": "request_availability",
  "preferred_window_from_seller": "tomorrow afternoon"
}
```

Ares owns free/busy reads and appointment creation. The LLM sees safe slot labels only, never private calendar event details.

## Structured response contract

Every Appointment Setter response must be strict JSON, validated before any send:

```json
{
  "reply_text": "Got it. Is the place vacant right now, rented, or are you living there?",
  "intent": "seller_qualification",
  "stage": "condition_occupancy",
  "lead_bucket": "warm",
  "qualification_score_delta": 8,
  "next_best_action": "ask_one_question",
  "needs_human": false,
  "appointment_ready": false,
  "calendar_action_requested": false,
  "nurture_recommended": false,
  "disqualified": false,
  "risk_flags": []
}
```

If JSON is invalid, unsafe, too long, or violates policy, Ares must not send it.

## Slack reporting

Route: `appointment_setter` / `SLACK_CHANNEL_APPOINTMENT_SETTER`.

Slack should get:

- hot seller / appointment-ready alerts
- manual takeover requests
- prompt-injection / sensitive-info attempts
- STOP / wrong-number / DNC events
- nurture recommendations
- disqualification reasons
- appointment booked/held/requested

Slack text must avoid full PII/contact dumps. Exact records stay in Ares/operator artifacts.

## Rollout

1. Offline simulator: no sends; normal/adversarial conversations.
2. Owned-number smoke: Martin only, max turns, expiry, no global seller auto-replies.
3. Slack approval mode: real inbound sellers interpreted; replies require Martin approval.
4. Limited auto-reply: scoped source/channel only, max turns, kill switches, hot/risky escalation.
5. Calendar: Cal.com/Google free-busy then Ares-created holds/events only.
6. Nurture: Appointment Setter recommends long nurture; Ares drafts SMS/email; Martin approves campaign activation.

## Verification suite

- Normal multi-turn seller qualification.
- Hot/warm/nurture/disqualified bucketing.
- Appointment-ready and calendar dry-run flows.
- Prompt injection: system prompt, API keys, private info, other leads, Martin personal details.
- STOP/wrong-number/DNC/legal/angry handling.
- Manual takeover and global/channel kill switch.
- No direct tool/provider/secret access from Appointment Setter.
- Slack approval mode produces no live sends.
- Mission Control Conversation Desk renders real-estate context and disabled/gated controls correctly.
