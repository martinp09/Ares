---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-16T02:58:00Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/worktrees/ares-main"
target_branch: "main"
back_office_spine_commit: "e898ee0"
previous_handoff_commit: "9f30d2f"
implementation_commit: "9c256bf"
---

# Ares TODO / Handoff

## Current status

Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. This slice turns qualified leads into canonical deal records with lane-aware task/document/risk templates, stage transition blockers, fire-list read models, Supabase runtime persistence, and a read-only Mission Control Deal Desk page.

The Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf` as an operational no-send system; handoff docs landed at `9f30d2f`, env preflight landed at `a859fd2`, and case-detail enrichment finished the last high-value probate enrichment gap. Trigger schedules default to live public probate source acquisition, live public case-detail page enrichment, and live public CAD/tax/land-record enrichment. Backend defaults those live intelligence lanes on, but Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and keeps every outbound path blocked.

Origin-main hardening cleanup landed on GitHub `main`: `709f714` adds the dynamic Montgomery PublicSearch land-record end date, live no-send smoke case-detail assertion, legacy `/crm/hubspot/*` `operator_approval=true` live-write gate, and CI; `be11aaa` tracks Docker deployment files and Docker CI.

VPS rebuild on `100.74.177.6` is complete. `/opt/ares/Ares` and `/opt/ares/worktrees/ares-main` are at `be11aaa`; `ares-api` and `ares-ui` images were rebuilt and are running healthy; Caddy backup is `/etc/caddy/Caddyfile.bak.20260516T023712Z`; Caddy routes now include `/crm*`, `/deals*`, `/sms-agent*`, and `/voice*`; Supabase migration `20260516011000_deal_spine_runtime` is applied. Verified through Caddy: `/health` 200, `/crm/hubspot/customization` GET 405, `/deals` 200, `/deals/fire-list` 200, and `/mission-control/probate-autopilot/health` 200.

Latest manual live no-send smoke (`docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/live-smoke-output.txt`) completed with Harris + Montgomery counties, `47` live public probate source records, `8` keep-now rows enriched, live CAD/tax/land-record calls attempted, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`.

Back Office Spine v0 verification passed pre-merge and post-merge: focused backend/deal/Supabase contracts => `26 passed`; full backend => `942 passed`; Mission Control => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` => passed; browser spot-check rendered Deal Desk with no console errors.

Cleanup verification on the `be76288` baseline passed: focused backend => `44 passed`; full backend => `945 passed`; Mission Control tests => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` and smoke/script py-compile => passed. GitHub Actions CI passed on `709f714` and `be11aaa`.

No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, live smoke, or Vercel deploys were executed by this cleanup. The only live mutations after approval were the VPS Docker/Caddy rebuild and the existing Supabase deal-spine migration.

## Primary handoff artifacts

- Back Office Spine v0 RPD: `/root/obsidian-vault/03-Experiments/Ares Real Estate Operating System RPD.md`
- Back Office Spine v0 QC: `docs/qc/2026-05-16/back-office-spine-v0/`
- Case-detail enrichment QC: `docs/qc/2026-05-15/probate-case-detail-enrichment/`
- Env preflight QC: `docs/qc/2026-05-15/probate-autopilot-env-preflight/`
- Env preflight command: `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live`
- Live operational PRD execution QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`
- Live no-send smoke command: `uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD`
- Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- HubSpot operating-spine QC index: `docs/qc/2026-05-14/README.md`

## Immediate next actions

1. Before production no-send deployment, run `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live` and configure durable `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` / `LEAD_MACHINE_ARTIFACT_ROOT`.
2. After production deployment, monitor the no-send Trigger schedule reports for aggregate source-run/enrichment health.
3. Keep Instantly enrollment/send, SMS/Vapi dispatch, paid skiptrace, and HubSpot batch mirror writes gated until separately approved.
4. Measure property-match lift from case-detail-derived party/address/context evidence; current case-detail layer records contact candidates but still does not assert seller authority.
5. Profile or cache Supabase control-plane hydration before heavy operator use of the deal spine; verified live `/deals` and `/deals/fire-list` are correct but currently take roughly 10-11 seconds on the VPS.

## Open product follow-ups

- Back Office Spine v0 follow-up: add operator actions for task completion/document review only after backend command contracts and approval gates are defined; current Deal Desk page is read-only.
- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
- Use case-detail-derived party/address/context evidence to improve deterministic property matching; current case-detail layer records contact candidates and keeps seller-authority verification false until separate evidence.
- Reacher/SMTP-capable email verification cannot run recipient-MX mailbox probes from the current Hetzner VPS while outbound port 25 is blocked; request unblock, move verifier sidecar, or use DNS/MX/disposable-only checks until egress is available.
- Enrich Harris probate exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend.
- Activate/upgrade the keyed Instantly workspace to a paid plan before real-account campaign sync/enrollment.
- Capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`.
- Add production monitoring/alerts for provider callback failures.

## Hard rules

- Do not make Mission Control frontend call Supabase directly.
- Do not run live SMS/email/calls/provider mutations without explicit approved recipients and gates.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the evidenced commit.
- Do not rewrite already-applied baseline migrations in place.
- Never print secrets into QC evidence, logs, reports, or chat.

## Minimum verification before future deploy/promotion

```bash
uv run pytest -q
npm --prefix apps/mission-control ci
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npm --prefix trigger ci
npm --prefix trigger run typecheck
git diff --check
git diff --cached --check
```
