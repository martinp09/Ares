# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/root/Ares-inspect`
- Active branch: `chore/activation-readiness-envfile-2026-05-10`
- Latest merged main: PR #8 at `39eb239122754e3fb2ed98b888d833a6b897a58f` (`chore: add activation readiness handoff`)
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Lease-options landing -> Ares intake/SMS/email/Slack/reminder backend plus activation handoff are merged to `main`; current branch makes the activation checker consume existing local env files safely, without copying or printing secrets.
- `scripts/activation_readiness.py --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults` now reuses available local credentials and derived callback/landing URLs; latest sanitized run is blocked by 5 external gates instead of the 17-key empty-checkout baseline.
- Remaining external gates from that run: live sends still disabled, invalid `RESEND_FROM_EMAIL`, missing Slack token/channel, missing `CAL_WEBHOOK_SECRET`, and hosted protected routes still return `401` with the local runtime key until Vercel production envs can be verified.
- Approved prior route smoke reached Ares provider routes; TextGrid returned `Balance is below 0`, and Resend was blocked by invalid `RESEND_FROM_EMAIL`.
- Security-audit hardening and Harris daily lead-machine foundation are merged to `main`; production wiring is live and must remain untouched unless explicitly requested.

## Current TODO
1. Set/fix remaining external provider/env gates, then rerun the env-file readiness command before any live smoke: `PROVIDER_LIVE_SENDS_ENABLED`, verified `RESEND_FROM_EMAIL`, Slack token/channel, `CAL_WEBHOOK_SECRET`, and production/Vercel runtime key alignment.
2. Set landing runtime envs in the deployment target: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
3. Update provider callback configurations externally if any deployed provider still references old query-string runtime-key callback URLs.
4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

## Recent Change
- 2026-05-10: Added env-file/local-default support to activation readiness so `/opt/ares/Ares/.env` can be checked safely without copying secrets; local dark intake smoke passes with live sends disabled, hosted protected route still needs production env/Vercel verification.
- 2026-05-10: Added non-secret activation readiness tooling/handoff docs after PR #7 merge.
- 2026-05-09: PR #7 merged landing -> Ares intake provider bundle: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold behind live-send gate, Cal.com `starts_at`, and Trigger-backed 24h/1h reminders with reschedule refresh.
- 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
- 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
