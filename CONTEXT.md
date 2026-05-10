# Context

## Stable Facts
- Repo: `martinp09/Ares`
- Current working checkout: `/root/Ares-inspect`
- Active branch: `chore/activation-readiness-handoff-2026-05-09`
- Latest merged main: PR #7 at `cda9c828` (`feat: expand landing intake contract`)
- Runtime production URL: `https://production-readiness-afternoon.vercel.app`
- Mission Control URL: `https://mission-control-g8un1ly0w-martins-projects-9600e79e.vercel.app`
- Supabase project ref: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`

## Current Scope
- Lease-options landing -> Ares intake/SMS/email/Slack/reminder backend is merged to `main`; current branch adds activation readiness tooling/docs only.
- `scripts/activation_readiness.py` reports Ares/landing live-launch gates without printing raw secrets; handoff is `docs/activation-readiness-handoff.md` and QC is `docs/qc/2026-05-10/activation-readiness-handoff/`.
- Local readiness verdict is blocked by expected env/provider gates: live sends disabled, TextGrid/Resend/Slack/Cal/Trigger provider env missing in this checkout, and landing runtime env not present in this shell.
- Approved prior route smoke reached Ares provider routes; TextGrid returned `Balance is below 0`, and Resend was blocked by invalid `RESEND_FROM_EMAIL`.
- Security-audit hardening and Harris daily lead-machine foundation are merged to `main`; production wiring is live and must remain untouched unless explicitly requested.

## Current TODO
1. Set/fix provider envs/accounts, then rerun `python scripts/activation_readiness.py --json` before any live smoke.
2. Set landing deployment envs: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
3. Update provider callback configurations externally if any deployed provider still references old query-string runtime-key callback URLs.
4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

## Recent Change
- 2026-05-10: Added non-secret activation readiness tooling/handoff docs after PR #7 merge.
- 2026-05-09: PR #7 merged landing -> Ares intake provider bundle: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold behind live-send gate, Cal.com `starts_at`, and Trigger-backed 24h/1h reminders with reschedule refresh.
- 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
- 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.

## Read These Sections In `memory.md`
1. `## Current Direction`
2. `## Open Work`
3. latest entry in `## Change Log`
