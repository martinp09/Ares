# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/root/Ares-inspect`
- Active branch: `main`
- Latest activation-readiness code commit: `9addc1de72ec2f80a86fb51f608d44eb24c4627e` (`chore: support env-file activation readiness`)
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Lease-options landing -> Ares intake/SMS/email/Slack/reminder backend plus activation handoff are merged to `main`; main now includes env-file activation checking so existing local env files can be used safely, without copying or printing secrets. Current messaging rule: landing page handles Cal.com redirect, SMS is confirmation-only, and email may carry the booking link fallback.
- `scripts/activation_readiness.py --env-file /opt/ares/Ares/.env --runtime-url https://production-readiness-afternoon.vercel.app --derive-local-defaults` reuses available local credentials and derived callback/landing URLs; latest sanitized run is blocked by 5 external gates instead of the 17-key empty-checkout baseline.
- Remaining external gates from the latest sanitized readiness run: live sends still disabled by default, `RESEND_FROM_EMAIL` is unquoted/misparsed in the local env-file readiness path and should be set as a quoted verified sender, missing Slack token/channel, missing `CAL_WEBHOOK_SECRET`, and hosted protected routes/landing submit still return auth/handoff failures with the local runtime key until Vercel production envs can be verified.
- 2026-05-10 approved local TextGrid live smoke after funding reached TextGrid through `POST /mission-control/outbound/sms/test`; first body to Martin `+1***5914` was later `failed - Blocked by Textgrid Content Filter`, while minimal retry `Ares test 2.` delivered. QC evidence: `docs/qc/2026-05-10/textgrid-live-smoke-after-funding/`.
- Security-audit hardening and Harris daily lead-machine foundation are merged to `main`; production wiring is live and must remain untouched unless explicitly requested.

## Current TODO
1. Set/fix remaining external provider/env gates, then rerun the env-file readiness command before broader live launch: keep `PROVIDER_LIVE_SENDS_ENABLED` safe by default until launch, set quoted verified `RESEND_FROM_EMAIL`/reply-to, choose/skip Slack token/channel, set `CAL_WEBHOOK_SECRET`, verify production/Vercel runtime key alignment, and content-filter smoke the actual TextGrid confirmation/reminder copy with status polling.
2. Set landing runtime envs in the deployment target: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
3. Update provider callback configurations externally if any deployed provider still references old query-string runtime-key callback URLs.
4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

## Recent Change
- 2026-05-10: Landing deploy submit debug reproduced `500 {"error":"Submission failed"}` with complete fields while invalid input still returned `422`; direct hosted Ares with the local runtime key returned `401`, so the active blocker is Vercel/Ares runtime key/env alignment. Landing PR #3 commit `806394e` adds clearer `ARES_INTAKE_FAILED` UI copy; QC in lease-options-landing `docs/qc/2026-05-10/form-submit-resend-debug/`.
- 2026-05-10: Resend setup check found API key valid and `send.limitleshome.com` verified/sending-enabled; set `RESEND_FROM_EMAIL="Limitless Home Solutions <hello@send.limitleshome.com>"` and `RESEND_REPLY_TO_EMAIL=hello@send.limitleshome.com` so env-file parsing does not truncate the display-name sender.
- 2026-05-10: Updated Ares intake messaging: SMS confirmation is now confirmation-only with no booking/Cal.com link; Resend email keeps the booking-link fallback because landing page submit already redirects to Cal.com.
- 2026-05-10: Added non-secret activation readiness tooling/handoff docs after PR #7 merge.
- 2026-05-09: PR #7 merged landing -> Ares intake provider bundle: TextGrid confirmation SMS, Resend confirmation email, Slack intake scaffold behind live-send gate, Cal.com `starts_at`, and Trigger-backed 24h/1h reminders with reschedule refresh.
- 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
- 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
