# Diff Summary — SMS / Resend / Vapi Agent Scaffold

## Runtime/API

- `app/api/sms_agent.py`
  - Adds protected SMS agent routes for generic outbound SMS dry-run/live send and TextGrid webhook alias.
- `app/services/sms_agent_service.py`
  - Adds TextGrid-backed deterministic SMS service using existing TextGrid helpers and message/conversation repositories.
  - Dry-runs by default while live sends are disabled.
  - Requires `contact_id` and `sms_consent_confirmed=true` before any live generic SMS send.
- `app/models/sms_agent.py`
  - Adds request/response contracts for SMS sends and webhook responses.
- `app/api/voice_agents.py`
  - Adds protected Vapi/voice routes for assistant creation, phone-number provisioning, outbound calls, and webhooks.
  - Enforces `X-Vapi-Secret` when provider webhook signatures are required.
- `app/services/providers/vapi.py`
  - Adds deterministic Vapi REST client for `/assistant`, `/phone-number`, and `/call`.
- `app/services/voice_agent_service.py`
  - Builds Vapi payloads for assistants, inbound phone numbers, outbound calls, and Server URL webhook responses.
  - Keeps Vapi provider mutations/calls dry-run unless both live gates are enabled.
- `app/models/voice_agents.py`
  - Adds Pydantic contracts for voice assistant, phone-number, outbound-call, provider-action, and webhook responses.
- `app/core/config.py`
  - Adds Vapi env settings and default model/voice values.
- `app/main.py`
  - Mounts `sms-agent` and `voice` routers behind the existing runtime bearer dependency.
- `app/models/__init__.py`
  - Exports SMS/voice scaffold models.

## Tests

- `tests/services/test_sms_agent_service.py`
  - Covers dry-run behavior, live TextGrid payload shape/logging, missing TextGrid config, and live contact/consent requirements.
- `tests/api/test_sms_agent.py`
  - Covers runtime auth, route/service wiring through FastAPI dependency override, and TextGrid webhook alias parsing.
- `tests/services/test_voice_agent_service.py`
  - Covers assistant dry-run payload, live-gated outbound call payload, assistant-request handling, and tool-call response shape.
- `tests/api/test_voice_agents.py`
  - Covers runtime auth, route/service wiring, Vapi webhook handling, and Vapi secret enforcement.
- `tests/providers/test_vapi.py`
  - Covers authenticated Vapi client request shape and missing-key failure.

## Docs / env / evidence

- `.env.example`
  - Adds Vapi env contract placeholders and keeps `VAPI_PROVIDER_LIVE_SENDS_ENABLED=false`.
- `README.md`
  - Documents new routes, SMS consent gate, Vapi dry-run/live gates, and Vapi webhook auth/header expectations.
- `TODO.md`
  - Adds Communication Agent Scaffold checklist and Resend CLI smoke status.
- `CONTEXT.md`
  - Repoints this worktree/branch and records current scope/status.
- `memory.md`
  - Updates current direction, runtime route surface, open work, and change log.
- `docs/qc/2026-05-10/sms-email-vapi-agent-scaffold/`
  - Adds QC report, focused/full test outputs, diff check, and sanitized Resend CLI smoke evidence.

## Live/provider side effects

- No live SMS was sent by the new SMS agent route.
- No Vapi resources/calls were created.
- Resend CLI smoke sent one test email to `delivered@resend.dev`; final status is `delivered` in sanitized evidence.
