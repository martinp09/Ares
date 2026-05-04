---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-04T10:55:00Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/Ares"
current_branch: "feature/copywriting-brain-offer-engine"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

Ares is production-ready for a controlled live operator rollout.

Live production evidence:

- Runtime: `https://production-readiness-afternoon.vercel.app`
- Supabase project: `awmsrjeawcxndfnggoxw`
- Trigger project: `proj_puouljyhwiraonjkpiki`
- Trigger worker: `20260425.6`
- Production evidence: `docs/rollout-evidence/production-2026-04-25.json`
- Preview/current-main evidence: `docs/rollout-evidence/preview-2026-04-25.json`

Proven live wiring:

- Runtime health/auth on production Vercel.
- Supabase-backed runtime state.
- Trigger lifecycle callbacks.
- Instantly reply webhook.
- TextGrid SMS send and signed form-encoded status callback.
- Cal.com booking webhook.
- Resend live email smoke.
- Rollback bundle at `/Users/solomartin/Projects/Ares-backups/2026-04-25-awmsrjeawcxndfnggoxw`.

Known caveat:

- Native `pg_dump` backup is not captured because the Supabase CLI container could not resolve the Supabase DB host from Colima. A REST table-export rollback bundle exists instead.

## Next product slice

### 0. Probate title-packet Supabase wiring

- [done] Rebuild `origin/feature/lead-machine-probate-intake` onto current `origin/main`.
- [done] Add `title_packets` Supabase migration with tenant FK, lead FK, RLS, indexes, and idempotent identity key.
- [done] Add `TitlePacketsRepository` with memory and `lead_machine_backend=supabase` paths.
- [done] Add `POST /mission-control/lead-machine/title-packets/import`.
- [done] Normalize title-packet imports into probate-intake leads and create idempotent manual-review tasks.
- [ ] Run final full backend verification before merge.

### 1. Dashboard UI polish

- [ ] Build the approved ARES dashboard theme direction.
- [ ] Use `docs/design/ares-dashboard-theme-2026-04-25.md` as the design source.
- [ ] Keep it a real dense Mission Control dashboard, not a game menu.
- [ ] Keep gothic/flame treatment concentrated around the `ARES` title and subtle dashboard accents.
- [ ] Preserve readability, operator density, and existing Mission Control workflows.

### 2. Harris probate outreach campaign

- [done] Use `docs/marketing/2026-04-30-harris-probate-hot-warm-cold-campaign.md` as the operator-review campaign plan.
- [done] Add/export HOT/WARM/COLD segment manifests from the current Harris probate lead data before any live sends.
- [done] Add a backend operator approval gate for Instantly/TextGrid/direct-mail enrollment.
- [ ] Add a dedicated Mission Control frontend campaign-launch review page; current API contract is live and approvals can be reviewed from the existing approvals surface.
- [ ] Enrich Harris probate exports with email/phone via Tracerfy before Instantly/TextGrid enrollment; single-record CRM skiptrace endpoint is wired at `POST /mission-control/records/{record_id}/skiptrace`, batch export enrichment remains next. Current artifact has direct-mail-ready rows only.

### 3. Ares copywriting brain / offer engine

- [done] Initialize repo-local LLM Wiki at `docs/copywriting-wiki/` with Hormozi/Sultanic/probate source notes and examples.
- [done] Add typed offer/copy asset models and services for the Harris probate `Inherited Property Exit Option`.
- [done] Upgrade `AresCopyService` from generic drafts to offer-first, pain-first Harris probate drafts.
- [done] Add Alen Sultanic Copy Hinge, high-response email formula, and offer-code/Rosetta Stone concepts to the wiki and generated offer/copy asset metadata.
- [done] Draft stronger Hormozi/Sultanic probate grand-slam offer: `docs/marketing/copy/2026-05-02-probate-grand-slam-offer-v1.md`.
- [done] Ingest REI multichannel marketing playbook into `docs/copywriting-wiki/` and add channel doctrine: email speed/testing, direct mail trust/persistence, SMS consent/inbound only.
- [done] Create full cold-email campaign packets and local Instantly backups for probate and tax/title-friction campaigns: `docs/marketing/campaigns/` and `docs/marketing/exports/instantly-campaign-backups-2026-05-02/`.
- [done] Patch Instantly API client request headers after Cloudflare 1010 on Python urllib fingerprint; live list-campaigns preflight now succeeds without provider mutation.
- [done] Upload probate and tax/title-friction campaigns to Instantly as draft 4-step active sequences; no leads, sends, or activation.
- [done] Create Instantly long-nurture subsequences for both draft campaigns; trigger on campaign completed without reply and preserve Day 45/75/105/150/210/300 cadence.
- [ ] Activate/upgrade the newly keyed Instantly workspace to a paid plan, then rerun real-account sync from `docs/marketing/exports/instantly-campaign-backups-2026-05-02/`; current new-key preflight is blocked by `HTTP 402 Payment Required`. QC: `docs/qc/2026-05-03/instantly-real-account-sync/`.
- [ ] Capture stronger primary Alen Sultanic source material beyond user-provided excerpts and update the wiki; automated transcript access is blocked from this environment.
- [ ] Add Mission Control read/approval endpoints for offer/copy assets.
- [ ] Add persistence for offer/copy assets after the generated v1 proves useful.

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
