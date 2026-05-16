---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-16T20:31:00Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/worktrees/ares-main"
target_branch: "main"
back_office_spine_commit: "e898ee0"
previous_handoff_commit: "9f30d2f"
implementation_commit: "9c256bf"
supabase_migration_commit: "5228ef5"
supabase_migration_qc_commit: "d0e3fb7"
production_readiness_commit: "fc99b75"
supabase_identity_adapter_commit: "6cd2d88"
---

# Ares TODO / Handoff

## Current status

Back Office Spine v0 landed on `main` at `e898ee0` and the local `feature/back-office-spine-v0` branch was deleted. This slice turns qualified leads into canonical deal records with lane-aware task/document/risk templates, stage transition blockers, fire-list read models, Supabase runtime persistence, and a read-only Mission Control Deal Desk page.

The Harris + Montgomery probate autopilot PRD implementation landed at `9c256bf` as an operational no-send system; handoff docs landed at `9f30d2f`, env preflight landed at `a859fd2`, and production readiness/deploy wrap landed at `fc99b75`. VPS `/opt/ares/Ares` is now deployed from `61f18de` (runtime rebuild commit; later docs commits may be newer); Docker `ares-api` and `ares-ui` were rebuilt/recreated from that commit, Docker `ares-api` has durable `/var/lib/ares/lead-machine` mounted, and production no-send env preflight is healthy for `limitless/prod` with `LEAD_MACHINE_BACKEND=supabase`, live intelligence gates true, and outbound/provider mutation gates false. Trigger schedules default to live public probate source acquisition, live public case-detail page enrichment, and live public CAD/tax/land-record enrichment, but Trigger cloud remains intentionally gated: Hermes Trigger CLI auth is recovered, prod version `20260516.2` is deployed with schedule-level no-op guards, Trigger prod env now points at the current Ares API through Tailscale Funnel `https://ares.tail485fd9.ts.net`, and protected probate health passes with the Trigger runtime key. `ARES_TRIGGER_SCHEDULES_ENABLED=false` remains explicit, so Hermes no-agent cron `815e1261ab2e` remains the active no-send CT scheduler/watchdog until one controlled Trigger no-send run is proven and cron is intentionally paused. Backend defaults those live intelligence lanes on, but Ares still requires explicit no-send approval metadata for live source/case-detail/enrichment runtime requests and keeps every outbound path blocked. Dedupe/manual-isolation hardening adds hashed probate source identities, same-scope prior-run dedupe, same-packet duplicate exclusion, `source_run_scope=autonomous` scheduled payloads, isolated manual Hermes runner state, remote Supabase durable identity schema `20260516131500_probate_source_identity_dedupe.sql` applied on 2026-05-16, and a production Supabase identity-ledger adapter used when `LEAD_MACHINE_BACKEND=supabase`; the post-adapter live no-send monitor then found Harris rows expose postback-only detail targets, now safely classified as incomplete (`case_detail_postback_only`) rather than blocked unsafe URLs. QC includes `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/`, `docs/qc/2026-05-16/probate-production-readiness-wrap/`, and the existing probate dedupe/source identity artifacts.

Origin-main hardening cleanup landed on GitHub `main`: `709f714` adds the dynamic Montgomery PublicSearch land-record end date, live no-send smoke case-detail assertion, legacy `/crm/hubspot/*` `operator_approval=true` live-write gate, and CI; `be11aaa` tracks Docker deployment files and Docker CI.

VPS edge/container hardening is complete and production probate runtime was advanced again to `61f18de`. `/opt/ares/Ares` is detached at runtime rebuild commit `61f18de`; `ares-api` and `ares-ui` are rebuilt/recreated with non-root users, `no-new-privileges`, dropped caps, and loopback-only Docker ports (`127.0.0.1:8000`, `127.0.0.1:8080`). Caddy remains bound only to tailnet `100.74.177.6:80`, the runtime bearer lives in root-only `/etc/caddy/ares-runtime.env`, and `ares-edge-firewall.service` drops public `eth0` traffic to Caddy/Supabase dev ports. Tailscale Funnel exposes only the FastAPI runtime at `https://ares.tail485fd9.ts.net` -> `127.0.0.1:8000` for Trigger/cloud callbacks; protected routes still return `401` without bearer and protected probate health returns `200 healthy` with the runtime key. `ares-api` has durable `/var/lib/ares/lead-machine` mounted read-write, production env preflight is healthy for `limitless/prod`, `/health` / UI local smokes pass, SMS processing is draft-only/no-auto-reply, and Slack notifications are configured. QC: `docs/qc/2026-05-16/vps-current-main-rebuild-trigger-funnel/`, `docs/qc/2026-05-16/vps-edge-container-hardening/`, and `docs/qc/2026-05-16/probate-production-readiness-wrap/`.

Historical VPS rebuild before later hardening: `/opt/ares/Ares` and `/opt/ares/worktrees/ares-main` were at `be11aaa`; `ares-api` and `ares-ui` images were rebuilt and healthy; Caddy backup was `/etc/caddy/Caddyfile.bak.20260516T023712Z`; Caddy routes included `/crm*`, `/deals*`, `/sms-agent*`, and `/voice*`; Supabase migration `20260516011000_deal_spine_runtime` was applied. Current deployment state is `61f18de` as described above.

Latest manual live no-send smoke (`docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/live-smoke-output.txt`) completed with Harris + Montgomery counties, `47` live public probate source records, `8` keep-now rows enriched, live CAD/tax/land-record calls attempted, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`.

Back Office Spine v0 verification passed pre-merge and post-merge: focused backend/deal/Supabase contracts => `26 passed`; full backend => `942 passed`; Mission Control => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` => passed; browser spot-check rendered Deal Desk with no console errors.

Cleanup verification on the `be76288` baseline passed: focused backend => `44 passed`; full backend => `945 passed`; Mission Control tests => `25 files / 82 tests`; Mission Control typecheck/build => passed; Trigger typecheck => passed; `git diff --check` and smoke/script py-compile => passed. GitHub Actions CI passed on `709f714` and `be11aaa`.

- No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, live smoke, Vercel deploys, or Supabase schema changes were executed by this adapter slice. The only live mutations after approval were the earlier VPS Docker/Caddy rebuild, the existing Supabase deal-spine migration, and the approved Supabase probate source identity migration.

## Primary handoff artifacts

- Back Office Spine v0 RPD: `/root/obsidian-vault/03-Experiments/Ares Real Estate Operating System RPD.md`
- Back Office Spine v0 QC: `docs/qc/2026-05-16/back-office-spine-v0/`
- Case-detail enrichment QC: `docs/qc/2026-05-15/probate-case-detail-enrichment/`
- Env preflight QC: `docs/qc/2026-05-15/probate-autopilot-env-preflight/`
- Env preflight command: `uv run python scripts/probate_autopilot_env_contract.py --env-file .env --require-scheduled-live`
- Live operational PRD execution QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`
- Live no-send smoke command: `uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD`
- Probate dedupe/isolation QC: `docs/qc/2026-05-16/probate-dedupe-runtime-isolation/`
- Supabase probate source identity migration: `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql` (applied remotely 2026-05-16)
- Remote Supabase probate source identity migration QC: `docs/qc/2026-05-16/probate-source-identity-supabase-migration/`
- Supabase probate source identity adapter QC: `docs/qc/2026-05-16/probate-source-identity-supabase-adapter/`
- Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- Probate production readiness wrap QC: `docs/qc/2026-05-16/probate-production-readiness-wrap/`
- HubSpot operating-spine QC index: `docs/qc/2026-05-14/README.md`

## Immediate next actions

1. Let one controlled Trigger no-send run execute against `https://ares.tail485fd9.ts.net`; if it proves no duplicate source runs and the expected no-send lifecycle, then set `ARES_TRIGGER_SCHEDULES_ENABLED=true` and pause Hermes cron `815e1261ab2e`.
2. Watch the next Hermes no-agent CT scheduler window for the next `limitless/prod` autonomous morning brief while Hermes remains authoritative.
3. Monitor the Funnel API edge (`/health`, protected probate health with bearer, protected routes `401` without bearer) and keep Tailscale Funnel limited to the API loopback proxy.
4. Add a Harris postback case-detail client if live Harris party/event/document detail completion is required; current postback-only rows are safely incomplete, not blocked.
5. Keep Instantly enrollment/send, SMS/Vapi dispatch, paid skiptrace, and HubSpot batch mirror writes gated until separately approved.
6. Monitor the tailnet-only Caddy UI/API edge and keep `ares-edge-firewall.service` active while Supabase/dev ports remain published by their owning stack.

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
