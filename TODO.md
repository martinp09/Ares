---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-15T20:20:00Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/worktrees/ares-main"
current_branch: "main"
---

# Ares TODO / Handoff

## Current status

The Harris + Montgomery probate autopilot source-foundation/live-adapter activation slice is landed on `main` as a disabled-by-default, no-send runtime capability. The slice adds public probate source adapters, source-run/idempotency foundations, Mission Control health surfaces, Trigger.dev schedule wrappers, file/local-export provider seams, live-source gates, live CAD/tax/land-record enrichment seams, activation runbook, and QC evidence.

No live county pulls, HubSpot batch writes, Instantly enrollment/sends, SMS/Vapi calls, paid skiptrace, Slack/provider sends, or deploys were executed by this slice.

HubSpot operating-spine work remains dry-run/gated except for the previously approved single-record canaries documented in QC. HubSpot live apply is still credential/scope-gated.

## Primary handoff artifacts

- Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- Probate live adapter activation QC: `docs/qc/2026-05-15/probate-autopilot-live-adapter-activation/`
- Probate source foundation QC: `docs/qc/2026-05-15/probate-autopilot-source-foundation/`
- Probate durable source rows QC: `docs/qc/2026-05-15/probate-autopilot-durable-source-rows/`
- Probate source-file adapter + operator health QC: `docs/qc/2026-05-15/probate-source-file-adapter-operator-health/`
- Probate autopilot doctor QC: `docs/qc/2026-05-15/probate-autopilot-doctor/`
- Probate source adapters + health surface QC: `docs/qc/2026-05-15/probate-source-adapters-health-surface/`
- Probate Mission Control health panel QC: `docs/qc/2026-05-15/probate-autopilot-mission-control-health-panel/`
- Probate source-provider bridge gate QC: `docs/qc/2026-05-15/probate-source-provider-bridge-gate/`
- Probate bigger gates QC: `docs/qc/2026-05-15/probate-autopilot-bigger-gates/`
- HubSpot operating-spine QC index: `docs/qc/2026-05-14/README.md`
- Provider sync/recovery runbook: `docs/runbooks/provider-sync-and-recovery.md`
- Operating cadence runbook: `docs/runbooks/agentic-company-operating-cadence.md`

## Immediate next actions

1. Before live county pulls, configure durable source-run/artifact paths, set source env gates deliberately, and run one manual no-send source pull per the activation runbook.
2. Keep `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=false` until the manual live-source pilot is reviewed.
3. Keep HubSpot batch mirror writes, Instantly enrollment/send, SMS/Vapi dispatch, paid skiptrace, and deploy as separate explicit approval gates.
4. For Instantly later, let inboxes continue warming, write/review exact copy first, then use only approved recipient/lead lists with verified contact info and existing gated enrollment/send paths.

## Open product follow-ups

- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
- Run a controlled no-send live-source pilot for Harris/Montgomery after durable state/artifacts are configured; preserve raw-first artifacts, idempotency, expected-counties SLA, source-count mismatch warnings, Mission Control Autopilot health visibility, and aggregate duplicate-case redaction.
- Reacher/SMTP-capable email verification cannot run recipient-MX mailbox probes from the current Hetzner VPS while outbound port 25 is blocked; request unblock, move verifier sidecar, or use DNS/MX/disposable-only checks until egress is available.
- Enrich Harris probate exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend.
- Activate/upgrade the keyed Instantly workspace to a paid plan before real-account campaign sync/enrollment.
- Capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`.
- Consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary.
- Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.
- Optionally replace the REST rollback bundle with native `pg_dump` once Supabase CLI container DNS is fixed.
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
npm --prefix apps/mission-control test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npm --prefix trigger run typecheck
git diff --check
git diff --cached --check
```
