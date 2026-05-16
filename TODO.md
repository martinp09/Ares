---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-16T02:15:00Z"
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

Origin-main hardening cleanup is active on `fix/origin-main-hardening-cleanup` in `/tmp/ares-hardening-cleanup`: Montgomery PublicSearch land-record windows now end on the current day instead of a frozen date, the reusable live no-send smoke asserts live case-detail calls, legacy `/crm/hubspot/*` live writes require `operator_approval=true`, and `.github/workflows/ci.yml` runs backend, Mission Control, Trigger, and whitespace gates.

Read-only VPS inspection on `100.74.177.6` found the live runtime is Docker/Caddy based: `/opt/ares/docker-compose.yml` builds `ares-api` and `ares-ui` from `/opt/ares/Ares`, Caddy routes API paths to `127.0.0.1:8000` and UI fallback to `127.0.0.1:8080`, and the running API image was built before the current probate/HubSpot routes. After the other workflow finished, `/opt/ares/Ares` is detached at `be76288` and `/opt/ares/worktrees/ares-main` is clean `main` at `be76288`; the Docker images still have 2026-04-27 timestamps and were not rebuilt. No server mutation or deploy was executed.

Latest manual live no-send smoke (`docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/live-smoke-output.txt`) completed with Harris + Montgomery counties, `47` live public probate source records, `8` keep-now rows enriched, live CAD/tax/land-record calls attempted, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`.

Back Office Spine v0 verification passed pre-merge and post-merge: focused backend/deal/Supabase contracts => `26 passed`; full backend => `942 passed`; Mission Control => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` => passed; browser spot-check rendered Deal Desk with no console errors.

Cleanup verification on the `be76288` baseline passed: focused backend => `44 passed`; full backend => `945 passed`; Mission Control tests => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` and smoke/script py-compile => passed.

No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, live smoke, production deploys, or provider mutations were executed by this cleanup.

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
5. Before VPS deployment, rebuild intentionally from the clean `be76288` deployment tree or a reviewed successor; current live Docker images still predate current-main routes.

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
