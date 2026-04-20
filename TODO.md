---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-20T12:32:10Z"
repo: "martinp09/Ares"
local_checkout: "/home/workspace/Hermes-Central-Command/.worktrees/loose-ends"
current_branch: "feature/loose-ends"
---

# Ares TODO / Handoff

## Live pointer

- `docs/superpowers/plans/2026-04-20-ralph-loop-full-implementation-plan.md`

## Source inputs

- `docs/superpowers/specs/Hermes — Instantly Lead Automation Final Spec 2026.md`
- `docs/superpowers/plans/2026-04-16-harris-probate-keep-now-ingestion-plan.md`
- `docs/superpowers/plans/2026-04-16-curative-title-cold-email-machine-plan.md`
- `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md` *(deprecated)*

## What is in this TODO

1. Execute the Ralph loop plan phase by phase.
2. Keep the source docs above as inputs, not separate live targets.
3. Do not reopen completed phases unless a regression appears.
4. Finish the remaining phases in order:
   - Phase 2 adapter contract gaps
   - Phase 4 replay-safe release management
   - Phase 5 Mission Control dogfood polish
   - Phase 6 internal catalog and marketplace
5. Keep the repo scoped to the master plan until the next explicit reopen.

## Notes

- The Ralph loop plan is now the authoritative execution map.
- The older implementation plan stays in the repo but is deprecated.
- The older docs remain valid source material, but they no longer drive the live TODO independently.

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
