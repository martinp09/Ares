# Ares Appointment Setter Conversation Desk QC Report

## Scope

Implemented the first bounded Appointment Setter / Conversation Desk continuation on `feature/ares-chief-of-staff-v0`.

This slice turns the SMS reply layer into a least-privilege real-estate acquisitions ISA contract and remodels the Mission Control Inbox around Chatwoot-style conversation desk patterns while keeping Ares as the source of truth.

## What changed

- Added current design/runbook docs:
  - `docs/superpowers/specs/2026-05-18-ares-appointment-setter-conversation-desk-design.md`
  - `docs/runbooks/ares-appointment-setter-conversation-desk.md`
- Added Appointment Setter runtime config gates:
  - `APPOINTMENT_SETTER_ENABLED`
  - `APPOINTMENT_SETTER_CALENDAR_ACTIONS_ENABLED`
  - `APPOINTMENT_SETTER_MAX_AUTO_REPLIES_PER_THREAD`
  - `SLACK_CHANNEL_APPOINTMENT_SETTER`
- Extended SMS reply decisions with acquisitions qualification state:
  - stage
  - lead bucket
  - qualification score
  - score breakdown
  - missing fields
  - next best action
  - appointment/calendar/nurture/disqualified flags
  - risk flags
- Added security-sensitive classification and handoff for prompt injection / sensitive-info requests.
- Added `manual_control` and `appointment_setter_paused` kill-switch enforcement before `auto_ack` can send.
- Updated Mission Control Inbox into a Conversation Desk view with Appointment Setter review context and disabled placeholder controls.
- Updated README / TODO / CONTEXT / memory with the current scope and next gates.

## Safety boundaries

No live side effects were performed:

- No seller SMS/email/calls.
- No global SMS auto-replies enabled.
- No TextGrid send from this implementation slice.
- No Slack post.
- No calendar / Cal.com / Google Calendar action.
- No paid skiptrace.
- No Instantly enrollment or upload.
- No HubSpot/provider write.
- No Supabase remote migration.
- No VPS deploy.
- No Telegram delivery for this workflow.

## Verification

Captured outputs:

- `test-output.txt`
  - Focused backend: `48 passed`
  - Mission Control typecheck: passed
  - Mission Control tests: `25 passed` files / `85 passed` tests
  - Mission Control production build: passed
  - `git diff --check`: passed
- `test-output-full-backend.txt`
  - Full backend: `1158 passed`

Fresh QC subagent review:

- Initial review found one blocker: documented `appointment_setter_paused=true` was not enforced before auto-ack.
- Blocker fixed by adding context propagation, policy handoff, and regression tests.
- Final review verdict: `PASS`, no blockers.

## Follow-up gates

Before making this live for real sellers:

1. Add real backend command endpoints for takeover / approve reply / request slots / nurture / disqualify.
2. Keep Mission Control controls disabled until those endpoints exist.
3. Configure `SLACK_CHANNEL_APPOINTMENT_SETTER` and Slack readiness.
4. Keep `SMS_AGENT_AUTO_REPLIES_ENABLED=false` until Martin approves a scoped production source/number.
5. Add a second-state reload before final provider send if future async workflows can change takeover state between decision and send.
6. Wire Cal.com / Google Calendar only through Ares-owned safe availability/booking adapters; never expose raw calendar credentials or event details to the LLM.
