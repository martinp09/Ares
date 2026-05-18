# Diff Summary

## Backend/config

- `.env.example`
  - Adds Appointment Setter env gates and dedicated Slack channel placeholder.
- `app/core/config.py`
  - Adds typed `APPOINTMENT_SETTER_*` settings and `SLACK_CHANNEL_APPOINTMENT_SETTER`.
- `app/services/sms_reply_agent_service.py`
  - Adds acquisitions qualification snapshot fields to `SmsReplyDecision`.
  - Adds prompt-injection / sensitive-info risk detection.
  - Adds lead scoring, stage, bucket, missing-field, next-action, nurture/calendar/disqualify classification.
  - Enforces global Appointment Setter gate, per-thread pause, manual takeover, and security-sensitive handoff before auto-ack.
  - Expands LLM prompt payload with sanitized qualification state and forbidden/allowed action boundaries.
- `app/services/sms_agent_service.py`
  - Propagates `manual_control`, `appointment_setter_paused`, and pause-like `conversation_status` values into reply context.

## Mission Control UI

- `apps/mission-control/src/lib/api.ts`
  - Extends `SmsAgentDecision` typing and mapper for Appointment Setter fields.
  - Routes conversation owner to `Martin` when reply review is required, otherwise `Appointment Setter`.
- `apps/mission-control/src/components/InboxList.tsx`
  - Rebrands the inbox as `Conversation Desk` with Ares-native source-of-truth copy.
- `apps/mission-control/src/components/ConversationThread.tsx`
  - Adds conversation owner/acquisition route/tags context.
  - Replaces generic SMS-agent review with Appointment Setter score/action/risk/missing-field panel.
  - Keeps takeover/approve/slots/nurture/disqualify controls disabled pending backend command contracts.
- `apps/mission-control/src/styles.css`
  - Adds Conversation Desk panel/grid/pill styling.
- `apps/mission-control/src/pages/InboxPage.test.tsx`
  - Updates assertions to the new Conversation Desk / Appointment Setter UI contract.

## Tests

- `tests/api/test_runtime_config_contract.py`
  - Ensures new env keys stay in `.env.example` contract.
- `tests/services/test_sms_reply_agent_service.py`
  - Adds prompt-injection/sensitive-info handoff coverage.
  - Adds manual takeover kill-switch coverage.
  - Adds conversation pause kill-switch coverage.
  - Adds appointment-ready qualification scoring coverage.
- `tests/services/test_sms_agent_service.py`
  - Adds process-pending regression proving `appointment_setter_paused=true` blocks auto-send under live-send + auto-ack gates.

## Docs/live handoff

- `docs/superpowers/specs/2026-05-18-ares-appointment-setter-conversation-desk-design.md`
- `docs/runbooks/ares-appointment-setter-conversation-desk.md`
- `README.md`
- `TODO.md`
- `CONTEXT.md`
- `memory.md`

## QC artifacts

- `docs/qc/2026-05-18/ares-appointment-setter-conversation-desk/REPORT.md`
- `docs/qc/2026-05-18/ares-appointment-setter-conversation-desk/diff-summary.md`
- `docs/qc/2026-05-18/ares-appointment-setter-conversation-desk/test-output.txt`
- `docs/qc/2026-05-18/ares-appointment-setter-conversation-desk/test-output-full-backend.txt`
