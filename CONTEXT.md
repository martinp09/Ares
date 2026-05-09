# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/root/Ares-inspect`
- Active branch after ship: `feat/landing-ares-intake-sms-agent`
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Landing-page -> Ares intake/SMS bridge is the active PR #7 branch `feat/landing-ares-intake-sms-agent`: Ares now accepts full seller-form context through `POST /marketing/leads`, preserves consent/UTM metadata, returns side-effect status, sends booking-link confirmation SMS/email when live-gated providers are configured, scaffolds Slack intake alerts behind the same live-send gate, and schedules Trigger-backed 24h/1h appointment reminders from Cal.com `starts_at` on booked/rescheduled events.
- Approved local route smoke to Martin's phone/email reached Ares provider routes with `PROVIDER_LIVE_SENDS_ENABLED=true`; TextGrid returned `Balance is below 0` before SMS delivery and Resend was blocked by invalid `RESEND_FROM_EMAIL`, so provider funding/sender env remains the live-send gate.
- Landing page branch `feat/landing-ares-intake-sms-agent` now routes `POST /api/contact` directly to Ares server-side; Supabase+n8n is no longer the active submit path.
- Security-audit hardening is complete and ready to operate from `main` after the merge of `hardening/ares-security-audit-patches-2026-05-09`.
- QC evidence: `docs/qc/2026-05-09/ares-security-audit-patches/`.
- Patched: secret/build-context hygiene, runtime auth fail-closed behavior, docs/auth/security headers, server-derived provider webhook trust, Cal/TextGrid/Instantly signature enforcement, global provider live-send gate, Mission Control no-browser-token behavior, Node/Python advisory cleanup, and Bandit static-scan cleanup.
- Verification passed: `git diff --check`, py compile, `uv run pytest -q` (`633 passed`), Trigger typecheck, Mission Control typecheck/build/full tests (`72 passed`), root/Trigger/Mission Control npm audits, pip-audit, and Bandit.
- Harris daily lead-machine foundation remains merged to `main` via PR #5; Slack and production promotion are still separate follow-ups.
- Production wiring is live and must remain untouched unless explicitly requested.

## Current TODO
1. Fix live provider env gates before claiming delivery: add TextGrid funds/valid sender account state, set verified `RESEND_FROM_EMAIL`, add `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE`, and set `CAL_BOOKING_URL`/Cal webhook env.
2. Deploy/update landing envs only after setting `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, and `BUSINESS_RUNTIME_ENVIRONMENT`; keep production promotion env-preserving.
3. Update provider callback configurations externally if any deployed provider still references old query-string runtime-key callback URLs.
4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

## Recent Change
- 2026-05-09: Added live-gated intake provider bundle on the Ares branch: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold, Cal.com `starts_at`, and Trigger-backed 24h/1h appointment reminders. Merge-readiness audit then tightened Slack behind the global live-send gate and made rescheduled Cal.com events refresh reminder scheduling without duplicate confirmations. Local approved route smoke hit TextGrid/Resend but delivery is blocked by TextGrid balance and invalid `RESEND_FROM_EMAIL`.
- 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
- 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.
- 2026-04-30: Added Harris probate campaign launch backend slice and QC at `docs/qc/2026-04-30/harris-probate-campaign-launch/`.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
