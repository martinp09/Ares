# Probate Production Readiness Wrap QC

- Date UTC: 2026-05-16
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/ares-main`
- Code commit deployed to VPS Docker: `fc99b75 Harden probate production readiness`
- Previous baseline: `bf76429 Harden probate live no-send monitor`
- Scope: finish as much production-readiness work as safely possible for Harris + Montgomery probate autopilot no-send intelligence.

## Final status

Status: **VPS runtime is deployed and production no-send env preflight is healthy.**

What is ready now:

- `/opt/ares/Ares` is detached at `origin/main` commit `fc99b75`.
- `ares-api` and `ares-ui` Docker images were rebuilt/recreated with image labels at `fc99b75`.
- `ares-api` has durable `/var/lib/ares/lead-machine` mounted read-write.
- `/opt/ares/Ares/.env` has non-secret probate no-send controls configured:
  - `LEAD_MACHINE_BACKEND=supabase`
  - durable source-run/artifact paths
  - `LEAD_MACHINE_BUSINESS_ID` / `LEAD_MACHINE_ENVIRONMENT=prod`
  - explicit live intelligence gates true
  - explicit outbound/provider mutation gates false
- Read-only env preflight now returns `status=healthy`, `no_send_ok=true`, `live_intelligence_ready=true`, `blockers=[]`.
- Tenant resolution succeeds for `limitless/prod` as business PK `1`.
- API health returns `{"status":"ok"}` and UI returns HTTP 200.

Still not fully done:

- Trigger.dev cloud deploy is blocked by CLI login/auth in this environment; see `trigger-deploy-output-sanitized.txt`.
- Hermes no-agent cron job `815e1261ab2e` remains active as a no-send CT scheduler/watchdog path and now reads `/opt/ares/Ares/.env`, uses `/opt/ares/Ares`, and writes under `/var/lib/ares/lead-machine`.
- Production Mission Control probate health currently returns `status=no_data` for `limitless/prod` because no autonomous prod brief exists yet after this deploy. The next scheduled window should create the first autonomous prod brief; manual forced run was isolated under `prod-manual`.

## Code changes made

- Hardened Harris postback source-row handling:
  - normalized rows now preserve `case_detail_postback_target` and `case_detail_source_url` top-level;
  - case-detail enrichment detects postback-only Harris rows from top-level and nested raw row fields;
  - incomplete live-detail payloads preserve their explicit `incomplete_reason`;
  - Harris parser no longer lets unrelated page-level ASP.NET links be associated with a probate result row.
- Updated runbook/context/memory for production durable env requirements and no-send provider gates.
- Added `.env.example` note that `LEAD_MACHINE_BACKEND=memory` is local-only; production no-send probate autopilot must use `supabase` for the durable identity ledger.

## Production runtime changes made outside git

These are host runtime changes, intentionally not committed because they include/localize deployment state:

- Backed up `/opt/ares/Ares/.env` and `/opt/ares/docker-compose.yml` with timestamped `.bak.*` files.
- Updated `/opt/ares/Ares/.env` with non-secret probate no-send controls; no raw secret values printed.
- Created/chowned durable host paths for container UID/GID `999:999`:
  - `/var/lib/ares/lead-machine`
  - `/var/lib/ares/lead-machine/artifacts`
  - `/var/lib/ares/lead-machine/manual_runs/*`
- Added `ares-api` volume mount:
  - `/var/lib/ares/lead-machine:/var/lib/ares/lead-machine`
- Rebuilt/recreated Docker services from `/opt/ares/Ares` at `fc99b75`.
- Hardened `/root/.hermes/scripts/ares_probate_autopilot_no_send.py` to:
  - load `/opt/ares/Ares/.env`;
  - use `/opt/ares/Ares` instead of the worktree;
  - use `/var/lib/ares/lead-machine` durable state/artifacts;
  - default to `limitless/prod` instead of `limitless/dev`;
  - keep provider/outbound gates false;
  - allow public read-only CAD/tax/land enrichment according to env gates.

## Verification

Repo verification before deploy:

- Focused probate/env tests: `52 passed`
- Full backend: `966 passed`
- Trigger typecheck: passed
- Code review subagent: APPROVED, no must-fix issues
- Final repo/QC ship-check subagent: APPROVED, no must-fix issues
- Final Hermes scheduler readiness subagent: APPROVED, no must-fix issues
- `git diff --check`: passed before commit

Production verification after deploy:

- Env preflight after config: `status=healthy`, `no_send_ok=true`, `live_intelligence_ready=true`, `blockers=[]`
- Tenant resolution: `limitless/prod` resolved to business PK `1`
- Docker compose: `ares-api` healthy, `ares-ui` running
- API health: `{"status":"ok"}`
- UI local HTTP: `200 OK`
- Docker image labels: `ares-api=fc99b75`, `ares-ui=fc99b75`
- Durable mount: `/var/lib/ares/lead-machine -> /var/lib/ares/lead-machine rw=true`
- Sanitized in-container env presence: lead-machine prod/no-send gates present and correct
- Manual forced Hermes cron smoke: completed, isolated as `environment=prod-manual`, `no_send_ok=true`, `outbound_allowed=false`, provider side effects all false, live CAD/tax/land attempted true, zero rows due current-day window.

Artifacts:

- `focused-test-output.txt`
- `full-backend-output.txt`
- `trigger-typecheck-output.txt`
- `env-preflight-before-deploy.json`
- `env-preflight-after-config.json`
- `tenant-resolution-output.txt`
- `post-deploy-verification.txt`
- `production-env-and-compose-summary.txt`
- `probate-health-smoke.txt`
- `hermes-cron-manual-force-now.json`
- `trigger-ci-output.txt`
- `trigger-prod-typecheck-output.txt`
- `trigger-deploy-output-sanitized.txt`
- `diff-summary.md`

## Env preflight before/after

Before production config, the deployed env check was blocked by missing:

- `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`
- `LEAD_MACHINE_ARTIFACT_ROOT`
- `LEAD_MACHINE_BUSINESS_ID`
- `LEAD_MACHINE_ENVIRONMENT`

After config:

- `status=healthy`
- `blockers=[]`
- `warnings=[]`
- `no_send_ok=true`
- `live_intelligence_ready=true`
- `side_effects.created_files_or_directories=false`
- `side_effects.live_source_calls=false`
- `side_effects.provider_mutations=false`

## Latest prior live no-send monitor evidence

Canonical monitor folder:

- `docs/qc/2026-05-16/probate-post-adapter-live-no-send-monitor/`

Two-day monitor result:

- source rows: `48`
- keep-now rows: `8`
- enriched rows: `8`
- source failed runs: `0`
- warnings: `0`
- SLA: `healthy`
- `no_send=true`
- `provider_sends_enabled=false`

Same-day strict smoke was failed/inconclusive because the date window had zero rows; runtime treats valid zero-row source pages as non-errors.

## No-send boundary

No outbound/provider mutation side effects were performed:

- no Instantly enrollment/sends
- no email/SMS/Vapi sends
- no paid skiptrace
- no HubSpot writes
- no Slack/provider sends
- no Supabase schema mutation in this wrap

Live/read-only public intelligence calls performed:

- Docker/local health checks
- tenant resolution read against Supabase
- manual forced Hermes cron smoke under `prod-manual`, with zero current-day rows and no provider mutations

## Scheduler status

- Trigger schedule code exists and typechecks, but cloud deploy is blocked by Trigger CLI login/auth.
- Hermes no-agent cron job `815e1261ab2e` is enabled every 10 minutes and only emits output on due CT windows. It now runs from deployed `/opt/ares/Ares`, reads the production env file, and uses durable `/var/lib/ares/lead-machine` state/artifacts.
- When Trigger cloud deploy/auth is recovered, choose one authoritative production scheduler to avoid duplicate autonomous source runs. Recommended long-term owner remains Trigger.dev; Hermes cron can be paused or kept as a manual/watchdog path.

## Immediate follow-ups

1. Recover Trigger.dev CLI auth and deploy `trigger/` from `fc99b75` or newer.
2. Watch the next Hermes CT window or Trigger schedule for the first `limitless/prod` autonomous morning brief.
3. Keep all outbound/provider-send gates false until Martin approves exact recipients/campaigns.
4. Build a dedicated Harris ASP.NET postback detail client later if live Harris party/event/document completion is required; current rows are safely incomplete, not blocked.
