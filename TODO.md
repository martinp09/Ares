---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-16T04:33:30Z"
repo: "martinp09/Ares"
local_checkout: "/home/workspace/Hermes-Central-Command"
current_branch: "feature/ares-enterprise-platform"
---

# Ares TODO / Handoff

## Live pointers

- `docs/superpowers/specs/Hermes — Instantly Lead Automation Final Spec 2026.md`
- `docs/superpowers/plans/2026-04-16-harris-probate-keep-now-ingestion-plan.md`
- `docs/superpowers/plans/2026-04-16-curative-title-cold-email-machine-plan.md`

## What is in this TODO

1. Implement the Harris County probate keep-now ingestion plan.
2. Implement the curative title cold email machine plan.
3. Implement the final Instantly-backed lead automation spec.
4. Build the data model:
   - `leads`
   - `lead_events`
   - `automation_runs`
   - `campaign_memberships`
   - `tasks`
5. Wire the Trigger.dev jobs:
   - `lead-intake`
   - `instantly-enqueue-lead`
   - `instantly-webhook-ingest`
   - `create-manual-call-task`
   - `followup-step-runner`
   - `suppression-sync`
   - `task-reminder-or-overdue`
6. Enforce the hard rule that only `email.sent` creates a manual call task.
7. Build Mission Control fixture views for the inbox, lead timeline, suppression state, and exceptions.
8. Verify idempotency, duplicate suppression, and webhook replay safety.

## Notes

- The old plan docs are active, not archived.
- Keep the repo scoped to these three live docs until the next explicit reopen.

## Bigger platform backlog

Yeah. The current slice is done; the next work is the bigger platform backlog.

What’s left, in order:

1. End-to-end contract tests for the whole turn loop
   - prove one turn can auth, preflight, stream, call tools, retry, compact, and show up in Mission Control
   - this is the last hardening item in the turn-engine plan

2. Phase 1: org tenancy and actor context
   - add org_id / memberships / actor resolution
   - keep business_id + environment alive during the transition
   - make Mission Control org-aware

3. Phase 3: enterprise controls
   - RBAC
   - secrets as first-class resources
   - append-only audit
   - usage accounting

4. Phase 4: release management
   - draft/candidate/published/deprecated/archived states
   - canary and rollback
   - replay lineage
   - evaluation-gated promotion

5. Phase 5: productize Mission Control
   - agent detail workflow
   - release panels
   - host adapter visibility
   - secrets/audit/usage surfaces
   - publish/rollback controls

6. Phase 6: internal catalog, then marketplace
   - internal install flow first
   - marketplace-ready distribution later
   - feature-flag the public side until dogfood proves it

If you want the highest-leverage next move, it’s the contract tests plus Phase 1. Org tenancy is the foundation. Everything else sits on that floor or falls through it.
