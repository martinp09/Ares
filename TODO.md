---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-25T14:06:36Z"
repo: "martinp09/Ares"
local_checkout: "/home/workspace/Hermes-Central-Command/.worktrees/lead-machine-probate-intake"
current_branch: "feature/lead-machine-probate-intake"
---

# Ares TODO / Handoff

## Live pointers

- `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
- `docs/superpowers/plans/2026-04-16-ares-lead-machine-implementation-plan.md`

## What is in this TODO

1. Execute the lead machine superfile and its implementation plan.
   - primary: Harris County probate keep-now ingestion
   - secondary: curative title cold email machine
   - shared: Instantly / Trigger.dev / Mission Control loop
2. Build the data model:
   - [done] `leads`
   - [done] `lead_events`
   - [done] `campaigns`
   - [done] `automation_runs`
   - [done] `campaign_memberships`
   - [done] `suppression`
   - [done] `tasks`
   - [done] in-memory repository + store wiring + package exports
3. Wire the Trigger.dev jobs:
   - `lead-intake`
   - `instantly-enqueue-lead`
   - `instantly-webhook-ingest`
   - `create-manual-call-task`
   - `followup-step-runner`
   - `suppression-sync`
   - `task-reminder-or-overdue`
4. Enforce the hard rule that only `email.sent` creates a manual call task.
5. Build Mission Control fixture views for the inbox, lead timeline, suppression state, and exceptions.
6. Verify idempotency, duplicate suppression, and webhook replay safety.
7. [done] Track Hermes-built Harris HOT title packets in Ares via `POST /mission-control/lead-machine/title-packets/import` and `TitlePacketImportService`; see `docs/superpowers/plans/2026-04-25-harris-hot-title-packet-import-runbook.md`.
8. [next] Promote title-packet `raw_payload` into first-class property/tax/probate/clerk/title-packet/operator-task records after canonical lead import proves useful.

## Notes

- The old plan docs are folded into the superfile and are now source notes, not separate live TODO items.
- Keep the repo scoped to the superfile until the next explicit reopen.

## Bigger platform backlog

The earlier turn-loop contract tests and Phase 1 org tenancy work are already done in prior sessions.

What’s left, in order:

1. Phase 3: enterprise controls
   - RBAC
   - secrets as first-class resources
   - append-only audit
   - usage accounting

2. Phase 4: release management
   - draft/candidate/published/deprecated/archived states
   - canary and rollback
   - replay lineage
   - evaluation-gated promotion

3. Phase 5: productize Mission Control
   - agent detail workflow
   - release panels
   - host adapter visibility
   - secrets/audit/usage surfaces
   - publish/rollback controls

4. Phase 6: internal catalog, then marketplace
   - internal install flow first
   - marketplace-ready distribution later
   - feature-flag the public side until dogfood proves it

Enterprise controls is the next slice.
