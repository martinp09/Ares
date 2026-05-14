---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-05-14T00:00:00Z"
repo: "martinp09/Ares"
local_checkout: "/opt/ares/Ares"
current_branch: "feature/copywriting-brain-offer-engine"
production_wiring_commit: "47be904"
---

# Ares TODO / Handoff

## Current status

HubSpot operating spine / agentic company Phases 1-9 are complete in the current prepared working tree. Phase 9 added final QC/readiness documentation, then the HubSpot portal customization itself was live-applied after operator instruction.

HubSpot live buildout result: Ares property groups/properties are present on contacts/deals/companies, and all 12 Ares stages are present in the existing HubSpot `Sales Pipeline` because the portal is limited to one deal pipeline.

Primary handoff artifacts:

- QC index: `docs/qc/2026-05-14/README.md`
- Final readiness: `docs/qc/2026-05-14/operating-spine-final-readiness/`
- Operating cadence runbook: `docs/runbooks/agentic-company-operating-cadence.md`
- Provider sync/recovery runbook: `docs/runbooks/provider-sync-and-recovery.md`
- HubSpot live buildout: `docs/qc/2026-05-14/hubspot-live-buildout/`
- Master plan status: `docs/superpowers/plans/2026-05-14-hubspot-operating-spine-agentic-company-plan.md`

Do not claim committed, merged, deployed, or promotable until the dirty/untracked working tree is staged/committed and reviewed intentionally.

## Immediate next actions

1. Review final readiness and HubSpot live-buildout evidence, then commit/open PR or equivalent review intentionally.
2. Keep deployment separate from commit/PR review; do not promote a commit different from the evidenced state.
3. Keep remaining live provider actions behind explicit operator approvals and env gates: HubSpot record sync, Instantly enroll/send, Vapi dispatch, source-provider pulls, Slack/provider sends.
4. If live provider rollout is approved later, start with preview/dry-run, narrow record scope, provider links/idempotency review, and evidence capture.

## Open product follow-ups

- Add Mission Control read/approval endpoints and frontend review page for Ares offer/copy assets and Harris probate campaign launch.
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
