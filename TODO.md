---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-15T22:37:26Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/worktrees/ares-main"
current_branch: "fix/probate-autopilot-enrichment-wiring"
---

# Ares TODO / Handoff

## Current status

The Harris + Montgomery probate autopilot PRD is now executed as an operational no-send system on this branch. Trigger schedules default to live public probate source acquisition plus live public CAD/tax/land-record enrichment, and the backend defaults those live lanes on. Ares still requires explicit no-send approval metadata for live source/enrichment runtime requests and keeps every outbound path blocked.

Latest manual live no-send smoke (`docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/live-smoke-output.txt`) completed with Harris + Montgomery counties, `47` live public probate source records, `8` keep-now rows enriched, live CAD/tax/land-record calls attempted, `sla_status=healthy`, `source_health_failed_runs=0`, `no_send=true`, and `provider_sends_enabled=false`.

No HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, or deploys were executed by this slice.

## Primary handoff artifacts

- Live operational PRD execution QC: `docs/qc/2026-05-15/probate-autopilot-live-operational-prd-execution/`
- Live no-send smoke command: `uv run python scripts/smoke/probate_autopilot_live_no_send_smoke.py --day YYYY-MM-DD`
- Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- Probate nightly enrichment wiring QC: `docs/qc/2026-05-15/probate-autopilot-enrichment-wiring/`
- Montgomery Odyssey adapter fix QC: `docs/qc/2026-05-15/montgomery-probate-odyssey-adapter/`
- Probate live adapter activation QC: `docs/qc/2026-05-15/probate-autopilot-live-adapter-activation/`
- HubSpot operating-spine QC index: `docs/qc/2026-05-14/README.md`

## Immediate next actions

1. Review/merge/push `fix/probate-autopilot-enrichment-wiring` after final diff check.
2. Keep Instantly enrollment/send, SMS/Vapi dispatch, paid skiptrace, and HubSpot batch mirror writes gated until separately approved.
3. If production deployment is requested, set durable state/artifact paths first: `LEAD_MACHINE_SOURCE_RUNS_STATE_PATH` and `LEAD_MACHINE_ARTIFACT_ROOT`.
4. Monitor the no-send cron reports for aggregate source-run/enrichment health after deployment.

## Open product follow-ups

- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
- Add stronger property matching once probate rows carry richer addresses/heir/applicant context; current live smoke proved live calls but 2026-05-15 keep-now rows still lacked enough property identifiers for CAD matches.
- Reacher/SMTP-capable email verification cannot run recipient-MX mailbox probes from the current Hetzner VPS while outbound port 25 is blocked; request unblock, move verifier sidecar, or use DNS/MX/disposable-only checks until egress is available.
- Enrich Harris probate exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend.
- Activate/upgrade the keyed Instantly workspace to a paid plan before real-account campaign sync/enrollment.
- Capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`.
- Consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary.
- Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.
- Add production monitoring/alerts for provider callback failures.
- Before live Vapi launch, configure Vapi Server URL credentials to send bearer auth and `X-Vapi-Secret`, then run an approved live smoke.
- Wire real Slack digest delivery only after Slack token/channels are available.

## Hard rules

- Do not make Mission Control frontend call Supabase directly.
- Do not run live SMS/email/calls/provider mutations without explicit approved recipients and gates.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the evidenced commit.
- Do not rewrite already-applied baseline migrations in place.
- Never print secrets into QC evidence, logs, reports, or chat.

## Minimum verification before merge/push

```bash
uv run pytest -q
npm --prefix trigger run typecheck
git diff --check
git diff --cached --check
```
