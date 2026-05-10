---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-10T02:34:04Z"
repo: "martinp09/Ares"
local_checkout: "/root/Ares-inspect"
current_branch: "main"
production_wiring_commit: "47be904"
activation_readiness_code_commit: "9addc1de72ec2f80a86fb51f608d44eb24c4627e"
---

# Ares TODO / Handoff

## Current status

Ares production wiring remains live for the controlled operator rollout. The Harris daily probate + HCAD `Estate Of` lead-machine foundation is merged to `main`; hosted preview smoke passed without Slack or provider sends. Security-audit hardening is merged to `main` with QC evidence at `docs/qc/2026-05-09/ares-security-audit-patches/`. The lease-options landing-page -> Ares intake/provider/reminder backend is merged to `main` via PR #7 at `cda9c828`; activation readiness handoff is merged via PR #8 at `39eb2391`; env-file activation readiness is merged to `main` at `9addc1d`.

Live production evidence:

- Runtime: `https://production-readiness-afternoon.vercel.app`
- Supabase project: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`
- Trigger worker: `20260425.6`
- Production evidence: `docs/rollout-evidence/production-2026-04-25.json`
- Preview/current-main evidence: `docs/rollout-evidence/preview-2026-04-25.json`

Known caveats:

- Native `pg_dump` backup is not captured because the Supabase CLI container could not resolve the Supabase DB host from Colima. A REST table-export rollback bundle exists instead.
- Slack digest delivery for the Harris daily import is intentionally last and blocked until `SLACK_BOT_TOKEN` plus target channels are available.
- Slack intake notification delivery for lease-option leads is scaffolded but blocked until `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` are available and `PROVIDER_LIVE_SENDS_ENABLED=true`.
- Local approved live TextGrid smoke to Martin `+1***5914` reached Ares Mission Control and TextGrid after funding was added; the first body was blocked by TextGrid Content Filter, then a minimal retry delivered. Resend remains blocked by invalid `RESEND_FROM_EMAIL` format before live email delivery can be claimed.
- Production promotion for the Harris daily import should be a dedicated handoff that preserves the production runtime/provider env contract; preview smoke passed at `https://production-readiness-afternoon-9adxg1gvb.vercel.app`.
- Deployed provider callback configurations should be checked/updated externally if any still use old `runtime_api_key` query-string URLs; runtime auth is now bearer-only plus provider signatures.

## Current product slice

### 0.5. Lease-options landing -> Ares intake bridge

- [done] Expand `POST /marketing/leads` to accept the full seller-form payload instead of a skinny contact record.
- [done] Preserve seller-fit fields, consent metadata, and attribution in Ares contact records/metadata.
- [done] Return `side_effects` so the landing page can show/log whether confirmation SMS/email/Trigger work was queued, skipped, or failed.
- [done] Add TextGrid confirmation SMS with E.164 normalization, confirmation-only copy, and STOP language; no booking link is sent over SMS.
- [done] Add Resend confirmation email with the booking link copy as the safer channel for Cal.com fallback.
- [done] Add server-side Slack `chat.postMessage` intake notifier scaffold with safe no-op when live sends are disabled or token/channel are missing.
- [done] Add Cal.com `starts_at` preservation plus Trigger-backed 24h/1h appointment reminder scheduling and `/marketing/internal/appointment-reminder` dispatch, including reschedule reminder refresh.
- [done] Gate confirmation SMS/email, Slack intake alerts, appointment reminders, and non-booker Trigger scheduling behind `PROVIDER_LIVE_SENDS_ENABLED`; first deploy remains no-live-send by default.
- [done] Replace the landing page active submit path with a server-side Ares bearer-auth handoff and remove Supabase+n8n active code.
- [done] Add `scripts/activation_readiness.py` plus `docs/activation-readiness-handoff.md` for non-secret launch gate checks and smoke sequencing; QC evidence at `docs/qc/2026-05-10/activation-readiness-handoff/`.
- [done] Add `--env-file`, `--runtime-url`, and `--derive-local-defaults` readiness options so `/opt/ares/Ares/.env` can be checked safely without copying secrets; latest sanitized run reduced the empty-checkout blocker list to 5 remaining external gates.
- [done] Run local dark Ares intake smoke with available local env and `PROVIDER_LIVE_SENDS_ENABLED=false`: provider status route returned 200, `POST /marketing/leads` returned 201, and SMS/email/Slack/Trigger side effects were skipped.
- [done] Approved local live TextGrid smoke to Martin `+1***5914` after funding: first body was later `failed - Blocked by Textgrid Content Filter`, then minimal retry `Ares test 2.` delivered; QC evidence at `docs/qc/2026-05-10/textgrid-live-smoke-after-funding/`.
- [blocked] Approved local route smoke to Martin's email reached Ares; Resend API/domain are valid, but `RESEND_FROM_EMAIL` must be set as a quoted verified sender identity before delivery smoke, e.g. `RESEND_FROM_EMAIL="Limitless Home Solutions <hello@send.limitleshome.com>"` and `RESEND_REPLY_TO_EMAIL=hello@send.limitleshome.com`.
- [blocked] Hosted protected Mission Control routes and direct hosted Ares `/marketing/leads` returned `401 Unauthorized` with the local runtime key; the deployed landing form reproduced a complete-field `500`, so Vercel/production env access is required to verify or update deployed `RUNTIME_API_KEY` and landing `BUSINESS_RUNTIME_API_KEY` alignment.
- [ ] Set landing runtime envs in the deployment target: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
- [ ] Set Ares runtime envs for live launch: valid `CAL_WEBHOOK_SECRET`, quoted verified `RESEND_FROM_EMAIL`/reply-to, chosen Slack behavior (`SLACK_BOT_TOKEN`/channel if Slack is used, or keep Slack optional/disabled), and TextGrid content-filter validation for the actual confirmation/reminder copy with status polling/callback evidence.

### 0. Security audit hardening

- [done] Add secret hygiene/build-context guardrails (`.gitignore`, `.dockerignore`, safer `.env.example`).
- [done] Make runtime auth bearer-only, constant-time, and fail-closed when `RUNTIME_API_KEY` is missing.
- [done] Protect docs/OpenAPI, add runtime/deploy security headers, and redact validation-error inputs.
- [done] Fail closed for provider webhook signatures by default and derive Instantly trust server-side.
- [done] Add global `PROVIDER_LIVE_SENDS_ENABLED=false` default and gate outbound enrollments, sequence dispatch, booking confirmations, and Mission Control test sends.
- [done] Remove browser runtime-token use from Mission Control and keep local dev proxy auth server-side.
- [done] Clear Node/Python dependency audits and Bandit findings.
- [done] Save QC evidence at `docs/qc/2026-05-09/ares-security-audit-patches/`.
- [done] Merge the security hardening patch set to `main`.
- [ ] Update production/provider callback configuration in a dedicated env-preserving handoff if any deployed callback still uses old query-string runtime-key URLs.

### 1. Harris daily lead-machine foundation

- [done] Add `POST /lead-machine/harris/daily-import` for daily Harris probate + HCAD `Estate Of` source payloads.
- [done] Default daily import to `dry_run=true` and require at least one source payload.
- [done] Process probate rows through deterministic keep-now/HCAD/scoring preview, with existing write path used when `dry_run=false`.
- [done] Process HCAD `Estate Of` rows into CRM source records/records/memberships when `dry_run=false`.
- [done] Preserve no-send behavior: `provider_send_count=0`, no Instantly/TextGrid/Resend sends, no Slack posts.
- [done] Add Slack readiness config fields without requiring credentials for dry-run/import.
- [done] Add Trigger runtime endpoint/types and `harris-daily-import` task wrapper.
- [done] Save QC evidence at `docs/qc/2026-05-09/harris-daily-lead-machine-foundation/`.
- [done] Commit and push `feat/harris-daily-lead-machine-foundation` to origin.
- [done] Open and merge PR #5 to `main`.
- [done] Deploy and smoke a hosted Vercel preview using authenticated `vercel curl`.
- [ ] Wire real Slack digest delivery only after Slack token/channels are available.
- [ ] Run dedicated production promotion only when intentionally preserving/updating production runtime/provider env wiring.

### 2. Harris probate outreach campaign

- [done] Use `docs/marketing/2026-04-30-harris-probate-hot-warm-cold-campaign.md` as the operator-review campaign plan.
- [done] Add/export HOT/WARM/COLD segment manifests from the current Harris probate lead data before any live sends.
- [done] Add a backend operator approval gate for Instantly/TextGrid/direct-mail enrollment.
- [ ] Add a dedicated Mission Control frontend campaign-launch review page; current API contract is live and approvals can be reviewed from the existing approvals surface.
- [ ] Add email/phone enrichment before Instantly/TextGrid enrollment; current artifact has direct-mail-ready rows only.

### 3. Dashboard UI polish

- [ ] Build the approved ARES dashboard theme direction from `docs/design/ares-dashboard-theme-2026-04-25.md`.
- [ ] Keep it a real dense Mission Control dashboard, not a game menu.
- [ ] Keep gothic/flame treatment concentrated around the `ARES` title and subtle dashboard accents.
- [ ] Preserve readability, operator density, and existing Mission Control workflows.

### 4. Production hardening follow-up

- [ ] Replace the REST rollback bundle with native `pg_dump` once Colima/Supabase DB DNS is fixed, if strict database restore fidelity is required.
- [ ] Add production monitoring/alerts for provider callback failures.
- [ ] Keep production evidence files updated after any provider or deployment changes.

## Hard rules

- Do not make Mission Control frontend call Supabase directly.
- Do not run live SMS/email without explicit approved recipients.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the evidenced commit.
- Do not rewrite already-applied baseline migrations in place.

## Minimum verification before merge/push

```bash
git diff --check
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run build
```

For the Harris daily backend/Trigger slice, completed verification is recorded in `docs/qc/2026-05-09/harris-daily-lead-machine-foundation/`.
