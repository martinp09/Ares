---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-21T00:00:00Z"
repo: "martinp09/Ares"
local_checkout: "/root/.config/superpowers/worktrees/Hermes-Central-Command/mission-control-enterprise-backlog"
current_branch: "feature/mission-control-enterprise-backlog"
---

# Ares TODO / Handoff

## Live pointers

- `docs/superpowers/plans/2026-04-21-mission-control-enterprise-backlog-master-plan.md`
- `docs/superpowers/plans/2026-04-13-hermes-mission-control-orchestration-plan.md`
- `docs/superpowers/plans/2026-04-15-ares-enterprise-agent-platform-implementation-plan.md`
- `docs/hermes-ares-integration-runbook.md`

## What is in this TODO

1. Execute the combined Mission Control + enterprise backlog plan on top of the current `main` baseline.
2. Treat the 2026-04-21 master plan as the canonical execution sequence for this branch.
3. Keep the 2026-04-13 Mission Control orchestration plan and the 2026-04-15 enterprise platform plan as live source inputs.
4. Preserve existing Supabase wiring and extend it additively.
5. Do not re-do already-landed Ares CRM / lead-machine phases unless a later phase explicitly requires it.

## Notes

- The older loose-ends MVP handoff is not the live scope for this branch.
- The enterprise-agent-platform plan was mistakenly marked deprecated; that has been corrected here.
- This branch is for the backlog after the currently merged Ares CRM baseline: org tenancy, host adapters, enterprise controls, release lifecycle, and Mission Control productization.
