---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-20T18:05:08Z"
repo: "martinp09/Ares"
local_checkout: "/home/workspace/Hermes-Central-Command/.worktrees/loose-ends"
current_branch: "feature/loose-ends"
---

# Ares TODO / Handoff

## Live pointers

- `docs/superpowers/specs/2026-04-16-ares-lead-machine-superfile.md`
- `docs/superpowers/plans/2026-04-16-probate-outbound-lease-option-inbound-mvp-implementation-plan.md`
- `docs/superpowers/plans/2026-04-17-ares-scaffold-completion-plan.md`
- `scripts/ralph/prd.json`
- `scripts/ralph/session-prompt.md`
- `scripts/ralph/watchdog.sh`
- `scripts/ralph/progress.txt`

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
- Ralph board milestones: `story-02-build-probate-outbound-write-path`, `story-03-harden-lease-option-inbound-lane`, `story-04-add-mission-control-dual-lane-surfaces`, `story-05-add-thin-opportunity-seam`, and `story-06-run-verification-and-rollout-gates` are verified done in this worktree.
- Story-06 verification evidence (memory-backed): `uv run pytest -q` (`257 passed`), Mission Control `typecheck` + `vitest --run` (`14 passed`) + `build`, `npm --prefix trigger run typecheck`, lease/probate fixture smokes, and health startup with Supabase env vars unset.
- Two blockers remain intentionally unfinished and need backend wiring before this branch is truly complete:
  - manual-review tasks created from ambiguous inbound SMS still need a durable live-backend persistence path; the current pass only protects the no-wire/memory-backed route
  - unknown-metadata TextGrid webhooks still need the live tenant-resolution/backend cutover path finished so the fallback/manual-review flow can run end-to-end without relying on deferred wiring
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
