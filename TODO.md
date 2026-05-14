---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-14T12:07:13Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/Ares"
current_branch: "feature/copywriting-brain-offer-engine"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

HubSpot operating spine / agentic company Phases 1-9 are complete and pushed on commit `8c19c26`. Phase 9 added final QC/readiness documentation, then the HubSpot portal customization itself was live-applied after operator instruction.

HubSpot live buildout result: Ares property groups/properties are present on contacts/deals/companies, and all 12 Ares stages are present in the existing HubSpot `Sales Pipeline` because the portal is limited to one deal pipeline.

HubSpot record-sync canary result: remote provider-links migration `20260514090000_provider_object_links.sql` is applied; local default HubSpot pipeline/stage env is set with gates off; one synthetic canary created HubSpot contact `486079925950` and deal `325110558439` with provider links.

HubSpot real-lead sync result: one hand-selected `limitless/prod` Harris probate lead (`lead_341`, case `543678`) was synced HubSpot-only after preview; HubSpot contact `485815102172` and deal `325123310274` were created with provider links `plink_3`/`plink_4`. No real batch sync, Instantly enrollment/send, Reacher call, Vapi call, source-provider pull, Slack send, or deploy side effect.

Primary handoff artifacts:

- QC index: `docs/qc/2026-05-14/README.md`
- Final readiness: `docs/qc/2026-05-14/operating-spine-final-readiness/`
- Operating cadence runbook: `docs/runbooks/agentic-company-operating-cadence.md`
- Provider sync/recovery runbook: `docs/runbooks/provider-sync-and-recovery.md`
- HubSpot live buildout: `docs/qc/2026-05-14/hubspot-live-buildout/`
- HubSpot record-sync canary: `docs/qc/2026-05-14/hubspot-record-sync-canary/`
- HubSpot real-lead sync: `docs/qc/2026-05-14/hubspot-real-lead-sync/`
- Reacher/SMTP egress check: `docs/qc/2026-05-14/reacher-smtp-egress/`
- Master plan status: `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md`

Do not claim merged, deployed, or promotable until the pushed branch is reviewed/merged intentionally. Local unrelated tracked/untracked files remain outside the pushed operating-spine/canary scope.

## Immediate next actions

1. Review/open PR or merge the pushed branch intentionally.
2. Keep deployment separate from branch review/merge; do not promote a commit different from the evidenced state.
3. For Instantly later, let inboxes continue warming, write/review the exact copy first, then only use an approved recipient/lead with verified contact info and the existing gated enrollment/send path.
4. Keep remaining live provider actions behind explicit operator approvals and env gates: HubSpot record batches, Instantly enroll/send, Vapi dispatch, source-provider pulls, Slack/provider sends.
5. If live provider rollout continues, start with preview/dry-run, narrow hand-selected records, provider links/idempotency review, and evidence capture.

## Open product follow-ups

- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
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
