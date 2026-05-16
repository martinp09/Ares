# Probate Production Readiness Wrap QC

- Date UTC: 2026-05-16
- Repo: `martinp09/Ares`
- Worktree: `/opt/ares/worktrees/ares-main`
- Starting commit: `bf76429 Harden probate live no-send monitor`
- Scope: finish as much production-readiness work as safely possible for Harris + Montgomery probate autopilot no-send intelligence.

## Status

Current status at initial wrap checkpoint: **production activation is env-gated until the deployed runtime env passes preflight**.

The live no-send intelligence path has green monitor evidence, and this slice adds final source-row/postback contract hardening. Outbound/provider mutation paths remain blocked.

## Changes made

- Hardened Harris postback source-row handling:
  - normalized rows now preserve `case_detail_postback_target` and `case_detail_source_url` top-level;
  - case-detail enrichment detects postback-only Harris rows from top-level and nested raw row fields;
  - incomplete live-detail payloads preserve their explicit `incomplete_reason`;
  - Harris parser no longer lets unrelated page-level ASP.NET links be associated with a probate result row.
- Updated runbook/context/memory for production durable env requirements and no-send provider gates.
- Added `.env.example` note that `LEAD_MACHINE_BACKEND=memory` is local-only; production no-send probate autopilot must use `supabase` for the durable identity ledger.

## Verification

- Focused probate/env tests: `52 passed`
- Full backend: `966 passed`
- Trigger typecheck: passed
- Code review subagent: APPROVED, no must-fix issues

Artifacts:

- `focused-test-output.txt`
- `full-backend-output.txt`
- `trigger-typecheck-output.txt`
- `diff-summary.md`

## Env preflight before deploy

Read-only command:

```bash
uv run python scripts/probate_autopilot_env_contract.py --env-file /opt/ares/Ares/.env --require-scheduled-live
```

Initial result is stored in `env-preflight-before-deploy.json`.

Initial blockers:

- `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`
- `LEAD_MACHINE_ARTIFACT_ROOT`
- `LEAD_MACHINE_BUSINESS_ID`
- `LEAD_MACHINE_ENVIRONMENT`

Initial safe state:

- `no_send_ok=true`
- no provider/outbound gates were enabled
- preflight is read-only and does not call county sources or mutate providers

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

No side effects in this wrap before deploy checkpoint:

- no Instantly enrollment/sends
- no email/SMS/Vapi sends
- no paid skiptrace
- no HubSpot writes
- no Slack/provider sends
- no Supabase schema mutation

## Production deploy requirements

Before declaring activated production no-send schedule readiness:

1. Deploy latest main to `/opt/ares/Ares` / Docker.
2. Configure `/opt/ares/Ares/.env` with:
   - `LEAD_MACHINE_BACKEND=supabase`
   - `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH`
   - `LEAD_MACHINE_ARTIFACT_ROOT`
   - `LEAD_MACHINE_BUSINESS_ID`
   - `LEAD_MACHINE_ENVIRONMENT`
   - explicit live intelligence gates true
   - explicit outbound/provider gates false
3. Mount durable lead-machine state/artifact path into `ares-api`.
4. Rerun preflight against the deployed runtime env and require:
   - `status=healthy`
   - `no_send_ok=true`
   - `live_intelligence_ready=true`
   - `blockers=[]`
5. Reconcile scheduler authority:
   - Trigger schedules are the intended production owner.
   - Hermes no-agent cron job `815e1261ab2e` exists separately and should be paused or constrained to manual/watchdog use if Trigger is activated, to avoid duplicate autonomous source runs.

## Post-deploy evidence

Pending in this checkpoint. This report should be updated after the runtime deploy/preflight/health checks finish.
