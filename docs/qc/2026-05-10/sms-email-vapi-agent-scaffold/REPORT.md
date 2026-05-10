# SMS / Resend / Vapi Agent Scaffold QC Report

Date: 2026-05-10
Branch: `feature/sms-email-vapi-agent-scaffold`
Worktree: `/opt/ares/worktrees/sms-email-vapi-agent-scaffold`
Base: `origin/main` at `b1bb6c1`

## Scope

This slice adds a deterministic communication-agent substrate to Ares without changing production envs or enabling live sends by default:

- Generic TextGrid SMS agent API:
  - `POST /sms-agent/messages`
  - `POST /sms-agent/webhooks/textgrid`
- Resend CLI setup/evidence:
  - installed `resend-cli v2.2.1`
  - verified `send.limitleshome.com` domain is enabled for sending
  - CLI test email to Resend's documented test recipient reached final `delivered`
- Vapi voice-agent scaffold:
  - `POST /voice/assistants`
  - `POST /voice/phone-numbers`
  - `POST /voice/calls/outbound`
  - `POST /voice/vapi/webhook`

## Safety posture

- No production env file was modified.
- No live Vapi assistant, phone number, or outbound call was created.
- Generic SMS sends dry-run by default while `PROVIDER_LIVE_SENDS_ENABLED=false`.
- Generic SMS live sends require TextGrid config, `contact_id`, and `sms_consent_confirmed=true`.
- Vapi provider mutations/calls require both `PROVIDER_LIVE_SENDS_ENABLED=true` and `VAPI_PROVIDER_LIVE_SENDS_ENABLED=true`.
- Vapi webhook route is still behind Ares runtime bearer auth; when provider signature enforcement is on, it also requires `X-Vapi-Secret` matching `VAPI_WEBHOOK_SECRET`.
- Resend CLI smoke used `/opt/ares/Ares/.env` in-process and wrote only sanitized domain/id/status evidence.

## Verification evidence

- Focused backend tests: `focused-test-output.txt`
  - `18 passed in 0.15s`
- Full backend suite: `full-test-output.txt`
  - `672 passed in 11.52s`
- Diff hygiene: `diff-check.txt`
  - `git diff --check` exited 0
- Resend CLI smoke: `resend-cli-smoke.json`
  - CLI: `resend-cli v2.2.1`
  - domain: `send.limitleshome.com`, `verified`, sending enabled
  - email id: `1d4172f1-765a-42cf-9a4a-029a5d2f5e5d`
  - recipient: `delivered@resend.dev`
  - final event: `delivered`

## Review notes

Parallel subagent review found three important issues, all addressed before final verification:

1. `VAPI_WEBHOOK_SECRET` existed but was not enforced.
   - Fix: `POST /voice/vapi/webhook` now validates `X-Vapi-Secret` when provider signatures are required.
2. SMS idempotency key was accepted without enforcing pre-send idempotency.
   - Fix: removed the misleading `idempotency_key` field from the public SMS agent request.
3. Generic SMS live-send route lacked an explicit consent/policy guard.
   - Fix: live generic SMS requires `contact_id` and `sms_consent_confirmed=true`.

## Remaining launch gates

- Configure Vapi Server URL credentials/headers externally before live callbacks: Ares bearer auth plus `X-Vapi-Secret`.
- Run a Vapi dry-run-to-live smoke only with approved phone numbers.
- Hosted landing/Ares production env alignment remains separate: landing runtime envs and production `RUNTIME_API_KEY` still need Vercel access.
- Ares route-level Resend delivery smoke remains separate from the CLI smoke; CLI/provider path is proven delivered.
