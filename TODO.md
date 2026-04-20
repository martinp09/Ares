---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-20T12:56:02Z"
repo: "martinp09/Ares"
local_checkout: "/home/workspace/Hermes-Central-Command/.worktrees/loose-ends"
current_branch: "feature/loose-ends"
---

# Ares TODO / Handoff

## Live pointers

- `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
- `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
- `docs/superpowers/plans/2026-04-17-ares-scaffold-completion-plan.md`

## What is in this TODO

1. Execute the probate outbound + lease-option inbound MVP implementation plan.
   - primary: Harris County probate outbound
   - secondary: lease-option inbound marketing
   - shared: Instantly / Trigger.dev / Mission Control loop
2. Keep the superfile and scaffold-completion plan as source inputs, not separate live targets.
3. Keep the 2026-04-15 enterprise-agent-platform implementation plan deprecated / archived.
4. Keep older completed Ares platform tasks archived instead of re-adding them to the live TODO.
5. Run the QC + devil's-advocate review loop when any new no-wire commits are added.
6. Finish operator/docs alignment across this repo and `Mailers AWF`.

## Notes

- The probate + lease-option plan is now the authoritative execution map.
- The older enterprise-platform plan stays in the repo but is deprecated.
- The older docs remain valid source material, but they no longer drive the live TODO independently.

## Bigger platform backlog

The broader Ares platform backlog remains archived for now.

What’s left, in order, after this MVP:

1. enterprise controls
   - RBAC
   - secrets as first-class resources
   - append-only audit
   - usage accounting

2. release management
   - draft/candidate/published/deprecated/archived states
   - canary and rollback
   - replay lineage
   - evaluation-gated promotion

3. productize Mission Control
   - agent detail workflow
   - release panels
   - host adapter visibility
   - secrets/audit/usage surfaces
   - publish/rollback controls

4. internal catalog, then marketplace
   - internal install flow first
   - marketplace-ready distribution later
   - feature-flag the public side until dogfood proves it
