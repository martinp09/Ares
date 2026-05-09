---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-09T16:05:03Z"
repo: "martinp09/Ares"
local_checkout: "/root/Ares-inspect"
current_branch: "main"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

Ares production wiring remains live for the controlled operator rollout. The Harris daily probate + HCAD `Estate Of` lead-machine foundation is merged to `main`; hosted preview smoke passed without Slack or provider sends. Security-audit hardening is complete with QC evidence at `docs/qc/2026-05-09/ares-security-audit-patches/` and is ready to operate from `main` after merge.

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
- Production promotion for the Harris daily import should be a dedicated handoff that preserves the production runtime/provider env contract; preview smoke passed at `https://production-readiness-afternoon-9adxg1gvb.vercel.app`.
- Deployed provider callback configurations should be checked/updated externally after this security branch lands if any still use old `runtime_api_key` query-string URLs; runtime auth is now bearer-only plus provider signatures.

## Current product slice

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
