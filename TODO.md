---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-15T19:47:50Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/worktrees/probate-autopilot-source-foundation"
current_branch: "feature/probate-autopilot-source-foundation"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

HubSpot operating spine / agentic company Phases 1-9 are complete and pushed on commit `8c19c26`. Phase 9 added final QC/readiness documentation, then the HubSpot portal customization itself was live-applied after operator instruction.

HubSpot live buildout result: Ares property groups/properties are present on contacts/deals/companies, and all 12 Ares stages are present in the existing HubSpot `Sales Pipeline` because the portal is limited to one deal pipeline.

HubSpot record-sync canary result: remote provider-links migration `20260514090000_provider_object_links.sql` is applied; local default HubSpot pipeline/stage env is set with gates off; one synthetic canary created HubSpot contact `486079925950` and deal `325110558439` with provider links.

HubSpot real-lead sync result: one hand-selected `limitless/prod` Harris probate lead (`lead_341`, case `543678`) was synced HubSpot-only after preview; HubSpot contact `485815102172` and deal `325123310274` were created with provider links `plink_3`/`plink_4`. Follow-up corrections added probate/heir/contact/mailing/property/tax-overlay fields, then mapped the applicant/mailing address into standard HubSpot contact `address/city/state/zip/country` fields for normal contact visibility. Current sync hash: `hubspot-real-lead-lead_341-visible-v4`. Email/phone/mobile and property/HCAD remain true data gaps. No real batch sync, Instantly enrollment/send, Reacher call, Vapi call, source-provider pull, Slack send, or deploy side effect.

Probate autopilot source-run foundation plus the next safe no-send PRD gates are implemented on this branch. It adds Harris+Montgomery no-send source-run manifests, PRD source-run fields, Trigger.dev CT schedule wrappers, optional file-backed source-run/idempotency state, metadata `source_rows` ingestion, artifact writing, safe source-file adapter/CLI, read-only Harris+Montgomery export adapter contract, repeatable source-packet CLI inputs, duplicate-case aggregate anomalies, read-only doctor CLI with freshness SLA, Mission Control health API/client, page-level Mission Control Autopilot health panel, disabled-by-default local-export source-provider bridge gate, dry-run source adapter preview (`adapter_preview`, default-off + approval-gated + no-network/no-browser), live Harris/Montgomery public probate source adapters behind explicit source approval plus `LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED`, optional schedule activation behind `LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED`, local/injectable property/CAD + tax + land-record/title-friction enrichment behind separate live-enrichment gates, outbound enqueue hard-blocks requiring explicit operator approval plus global/Instantly live gates, SLA/anomaly brief sections, operator next-action brief sections, and the no-send activation runbook. QC: `docs/qc/2026-05-15/probate-autopilot-source-foundation/`, `docs/qc/2026-05-15/probate-autopilot-durable-source-rows/`, `docs/qc/2026-05-15/probate-source-file-adapter-operator-health/`, `docs/qc/2026-05-15/probate-autopilot-doctor/`, `docs/qc/2026-05-15/probate-source-adapters-health-surface/`, `docs/qc/2026-05-15/probate-autopilot-mission-control-health-panel/`, `docs/qc/2026-05-15/probate-source-provider-bridge-gate/`, `docs/qc/2026-05-15/probate-autopilot-bigger-gates/`, and `docs/qc/2026-05-15/probate-autopilot-live-adapter-activation/`. No live county pulls were executed in this slice, and there were no HubSpot batch writes, skiptrace spend, Instantly enrollment/send, SMS, Vapi, Slack, direct-mail, or deploy side effects.

Primary handoff artifacts:

- QC index: `docs/qc/2026-05-14/README.md`
- Final readiness: `docs/qc/2026-05-14/operating-spine-final-readiness/`
- Operating cadence runbook: `docs/runbooks/agentic-company-operating-cadence.md`
- Provider sync/recovery runbook: `docs/runbooks/provider-sync-and-recovery.md`
- HubSpot live buildout: `docs/qc/2026-05-14/hubspot-live-buildout/`
- HubSpot record-sync canary: `docs/qc/2026-05-14/hubspot-record-sync-canary/`
- HubSpot real-lead sync: `docs/qc/2026-05-14/hubspot-real-lead-sync/`
- HubSpot rich probate/heir fields: `docs/qc/2026-05-14/hubspot-rich-probate-fields/`
- HubSpot contact visibility correction: `docs/qc/2026-05-14/hubspot-contact-visibility-correction/`
- Probate autopilot source foundation: `docs/qc/2026-05-15/probate-autopilot-source-foundation/`
- Probate autopilot durable source rows: `docs/qc/2026-05-15/probate-autopilot-durable-source-rows/`
- Probate source-file adapter + operator health: `docs/qc/2026-05-15/probate-source-file-adapter-operator-health/`
- Probate autopilot doctor: `docs/qc/2026-05-15/probate-autopilot-doctor/`
- Probate source adapters + health surface: `docs/qc/2026-05-15/probate-source-adapters-health-surface/`
- Probate Mission Control health panel: `docs/qc/2026-05-15/probate-autopilot-mission-control-health-panel/`
- Probate source-provider bridge gate: `docs/qc/2026-05-15/probate-source-provider-bridge-gate/`
- Probate bigger gates: `docs/qc/2026-05-15/probate-autopilot-bigger-gates/`
- Probate live adapter activation: `docs/qc/2026-05-15/probate-autopilot-live-adapter-activation/`
- Probate no-send activation runbook: `docs/runbooks/harris-montgomery-probate-autopilot-no-send-activation.md`
- Reacher/SMTP egress check: `docs/qc/2026-05-14/reacher-smtp-egress/`
- Master plan status: `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md`

Do not claim merged, deployed, or promotable until the pushed probate-autopilot branch is reviewed/merged intentionally. Live county pulls, CRM mirror writes, and outbound/provider actions remain separate approval gates.

## Immediate next actions

1. Review/merge the probate-autopilot source-foundation branch intentionally against `origin/main`; it is still a branch until committed, pushed, merged, and cleaned up.
2. Before live county pulls, configure durable source-run/artifact paths, set both source env gates deliberately, and run one manual no-send source pull per the activation runbook; leave schedule live activation off until the manual run is reviewed.
3. Keep the Mission Control Autopilot page read-only and sourced from `GET /mission-control/probate-autopilot/health`; do not add provider mutation buttons there until separate approval gates exist.
4. Keep deployment separate from branch review/merge; do not promote a commit different from the evidenced state.
5. For Instantly later, let inboxes continue warming, write/review the exact copy first, then only use an approved recipient/lead with verified contact info and the existing gated enrollment/send path.
6. Keep remaining live provider actions behind explicit operator approvals and env gates: HubSpot record batches, Instantly enroll/send, Vapi dispatch, source-provider pulls, Slack/provider sends.
7. If live provider rollout continues, start with preview/dry-run, narrow hand-selected records, provider links/idempotency review, and evidence capture.

## Open product follow-ups

- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
- Probate autopilot next phase: run a controlled no-send live-source pilot for Harris/Montgomery after durable state/artifacts are configured; preserve raw-first artifacts, idempotency, expected-counties SLA, source-count mismatch warnings, Mission Control Autopilot health visibility, and aggregate duplicate-case redaction.
- Reacher/SMTP-capable email verification cannot run recipient-MX mailbox probes from the current Hetzner VPS while outbound port 25 is blocked; request unblock, move verifier sidecar, or use DNS/MX/disposable-only checks until egress is available.
- Enrich Harris probate exports with email/phone via Tracerfy only after Martin explicitly approves skiptrace spend.
- Activate/upgrade the keyed Instantly workspace to a paid plan before real-account campaign sync/enrollment.
- Capture stronger primary Alen Sultanic source material and update `docs/copywriting-wiki/`.
- Consider an atomic backend bulk-record endpoint if large batch throughput/transaction semantics become necessary.
- Defer owner/property graph, research cockpit, and map UI until Records and stage model are stable.
- Optionally replace the REST rollback bundle with native `pg_dump` once Supabase CLI container DNS is fixed.
- Add production monitoring/alerts for provider callback failures.

## Hard rules

- Do not make Mission Control frontend call Supabase directly.
- Do not run live SMS/email/calls/provider mutations without explicit approved recipients and gates.
- Do not use fixture-backed UI success as production proof.
- Do not promote a commit different from the evidenced commit.
- Do not rewrite already-applied baseline migrations in place.
- Never print secrets into QC evidence, logs, reports, or chat.

## Minimum verification before merge/push

```bash
python -m pytest -q
npm --prefix apps/mission-control test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
npm --prefix trigger run typecheck
git diff --check
```
