---
title: "Ares TODO / Handoff"
status: active
updated_at: "2026-04-24T00:00:00-05:00"
repo: "martinp09/Ares"
local_checkout: "/Users/solomartin/Projects/Ares-full-stack-cohesion"
current_branch: "feature/ares-full-stack-cohesion-clean"
---

# Ares TODO / Handoff

## Live pointer

The current implementation blueprint is:

- `docs/superpowers/plans/2026-04-24-ares-full-stack-cohesion-mega-plan.md`

Supporting source map:

- `docs/superpowers/plans/2026-04-24-ares-supabase-wiring-from-memory.md`

## Completed slices

Phase 0 + Phase 1:

- full-stack cohesion spec
- clean `.env.example`
- Hermes/Ares/Trigger/Supabase runbook
- config contract tests
- Trigger runtime API static contract test
- Vite dev proxy for authenticated Mission Control API calls without exposing a public runtime key
- no Supabase migrations
- no live SMS/email sends

Phase 2:

- Supabase control-plane transaction now snapshots, flushes, deletes, and restores core `commands`, `approvals`, `runs`, `events`, and `artifacts`.
- Rollback restore is FK-safe for command/run/event/artifact tables, including parent-before-child replay runs.
- Regression coverage covers core deletions, update rollback, bigint canonicalization, and failed flush restore.

Phase 3:

- Added `docs/hermes-ares-runtime-adapter-contract.md`.
- Added `scripts/smoke_hermes_runtime_adapter.py`.
- Added Hermes tool payload-stability coverage.

Phase 4:

- Standardized Trigger lifecycle callback payloads to Ares snake_case callback models.
- Added required lifecycle reporting for run-mapped lead-machine jobs.
- Kept scheduled marketing sequence jobs lifecycle-optional so existing non-run Trigger scheduling still works.
- Removed stale `create-manual-call-task` Trigger job ID and kept the planned `marketing-create-manual-call-task` ID.
- Enforced per-lead queue keys for lease-option sequence and manual-call child jobs.
- Persisted `trigger_run_id` from artifact callbacks.

## Hard rules

- Do not install Ares into Hermes.
- Do not make Hermes, Trigger.dev, providers, or Mission Control the source of truth.
- Do not let Mission Control frontend call Supabase directly.
- Do not rewrite already-applied baseline migrations in place.
- Do not remove `business_id + environment` while adding `org_id`.
- Do not run live provider sends without explicit opt-in recipient flags.
- Preserve the existing dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` until it is intentionally reconciled.

## Latest verification

```bash
git diff --check
uv run pytest tests/smoke/test_health.py tests/api/test_runtime_config_contract.py tests/api/test_trigger_contract_files.py -q
uv run pytest tests/db/test_supabase_control_plane_client.py tests/db/test_control_plane_supabase_adapters.py -q
uv run pytest tests/api/test_commands.py tests/api/test_approvals.py tests/api/test_runs.py tests/api/test_replays.py tests/api/test_trigger_callbacks.py tests/api/test_hermes_tools.py tests/api/test_lead_machine_trigger_contract.py tests/api/test_marketing_sequence.py tests/api/test_marketing_leads.py -q
uv run pytest -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run test -- --run
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control run build
```

## Next gate

Start Phase 5 provider adapter cohesion next.
