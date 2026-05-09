---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-09T06:16:00Z"
repo: "martinp09/Ares"
local_checkout: "/root/Ares-inspect"
current_branch: "feat/harris-daily-lead-machine-foundation"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

Ares production wiring remains live for the controlled operator rollout. The current local branch adds the Harris daily probate + HCAD `Estate Of` lead-machine foundation and has not been deployed.

Live production evidence:

- Runtime: `https://production-readiness-afternoon.vercel.app`
- Supabase project: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`
- Trigger worker: `20260425.6`
- Production evidence: `docs/rollout-evidence/production-2026-04-25.json`
- Preview/current-main evidence: `docs/rollout-evidence/preview-2026-04-25.json`

Known caveats:

- Native `pg_dump` backup is not captured because the Supabase CLI container could not resolve the Supabase DB host from Colima. A REST table-export rollback bundle exists instead.
- Slack digest delivery for the Harris daily import is blocked until `SLACK_BOT_TOKEN` and target channels are available.
- Vercel deployment/hosted smoke for the Harris daily import branch is blocked until Vercel auth is available.

## Current product slice

### 0. Harris daily lead-machine foundation

- [done] Add `POST /lead-machine/harris/daily-import` for daily Harris probate + HCAD `Estate Of` source payloads.
- [done] Default daily import to `dry_run=true` and require at least one source payload.
- [done] Process probate rows through deterministic keep-now/HCAD/scoring preview, with existing write path used when `dry_run=false`.
- [done] Process HCAD `Estate Of` rows into CRM source records/records/memberships when `dry_run=false`.
- [done] Preserve no-send behavior: `provider_send_count=0`, no Instantly/TextGrid/Resend sends, no Slack posts.
- [done] Add Slack readiness config fields without requiring credentials for dry-run/import.
- [done] Add Trigger runtime endpoint/types and `harris-daily-import` task wrapper.
- [done] Save QC evidence at `docs/qc/2026-05-09/harris-daily-lead-machine-foundation/`.
- [done] Commit and push `feat/harris-daily-lead-machine-foundation` to origin.
- [ ] Open PR/merge after operator review.
- [ ] Wire real Slack digest delivery only after Slack token/channels are available.
- [ ] Deploy/smoke hosted runtime only after Vercel auth is available.

### 1. Harris probate outreach campaign

- [done] Use `docs/marketing/2026-04-30-harris-probate-hot-warm-cold-campaign.md` as the operator-review campaign plan.
- [done] Add/export HOT/WARM/COLD segment manifests from the current Harris probate lead data before any live sends.
- [done] Add a backend operator approval gate for Instantly/TextGrid/direct-mail enrollment.
- [ ] Add a dedicated Mission Control frontend campaign-launch review page; current API contract is live and approvals can be reviewed from the existing approvals surface.
- [ ] Add email/phone enrichment before Instantly/TextGrid enrollment; current artifact has direct-mail-ready rows only.

### 2. Dashboard UI polish

- [ ] Build the approved ARES dashboard theme direction from `docs/design/ares-dashboard-theme-2026-04-25.md`.
- [ ] Keep it a real dense Mission Control dashboard, not a game menu.
- [ ] Keep gothic/flame treatment concentrated around the `ARES` title and subtle dashboard accents.
- [ ] Preserve readability, operator density, and existing Mission Control workflows.

### 3. Production hardening follow-up

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

For the current backend/Trigger-only branch, completed verification is recorded in `docs/qc/2026-05-09/harris-daily-lead-machine-foundation/`.
