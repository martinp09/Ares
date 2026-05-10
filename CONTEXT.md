# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/opt/ares/worktrees/sms-email-vapi-agent-scaffold`
- Active branch: `feature/sms-email-vapi-agent-scaffold`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Communication-agent scaffold slice: generic TextGrid SMS agent, Resend CLI live test evidence, and Vapi voice-agent scaffold for assistants, phone numbers, outbound calls, and Server URL webhooks.
- New SMS route is deterministic and consent-gated for live sends: `POST /sms-agent/messages` dry-runs by default and requires `contact_id` plus `sms_consent_confirmed=true` when live sends are enabled.
- New Vapi routes stay dry-run unless both `PROVIDER_LIVE_SENDS_ENABLED=true` and `VAPI_PROVIDER_LIVE_SENDS_ENABLED=true`; Vapi webhooks require runtime bearer auth and, when provider signatures are required, `X-Vapi-Secret` matching `VAPI_WEBHOOK_SECRET`.
- Resend CLI `resend-cli v2.2.1` is installed; CLI smoke email `1d4172f1-765a-42cf-9a4a-029a5d2f5e5d` to `delivered@resend.dev` reached final `delivered` status using verified `send.limitleshome.com`.

## Current TODO
1. Finish ship gate for this branch: stage/commit/push after QC artifacts and diff checks are current.
2. Before live Vapi launch, configure Vapi Server URL credentials/headers to send Ares bearer auth and `X-Vapi-Secret`.
3. Set/fix remaining external provider/env gates before broader live launch: keep live sends safe by default, decide Slack token/channel, set `CAL_WEBHOOK_SECRET`, verify production/Vercel runtime key alignment, and content-filter smoke actual TextGrid confirmation/reminder copy with status polling.
4. Set landing runtime envs in deployment target: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
5. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

## Recent Change
- 2026-05-10: Added generic SMS agent and Vapi voice-agent scaffold with tests/QC under `docs/qc/2026-05-10/sms-email-vapi-agent-scaffold/`; full backend verification is `672 passed`.
- 2026-05-10: Installed Resend CLI and verified delivered CLI smoke through `send.limitleshome.com`; sanitized evidence is `docs/qc/2026-05-10/sms-email-vapi-agent-scaffold/resend-cli-smoke.json`.
- 2026-05-10: Production landing fix keeps public submit on Ares-backed route but Vercel contact-intake envs remain missing.
- 2026-05-10: Updated Ares intake messaging: SMS confirmation is confirmation-only with no booking/Cal.com link; Resend email keeps the booking-link fallback.
- 2026-05-09: PR #7 merged landing -> Ares intake provider bundle with TextGrid, Resend, Slack scaffold, Cal.com starts_at, and Trigger reminders.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
