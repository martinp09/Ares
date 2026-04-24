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

## Active slice

Phase 0 + Phase 1 only:

- full-stack cohesion spec
- clean `.env.example`
- Hermes/Ares/Trigger/Supabase runbook
- config contract tests
- Trigger runtime API static contract test
- Vite dev proxy for authenticated Mission Control API calls without exposing a public runtime key
- no Supabase migrations
- no live SMS/email sends

## Hard rules

- Do not install Ares into Hermes.
- Do not make Hermes, Trigger.dev, providers, or Mission Control the source of truth.
- Do not let Mission Control frontend call Supabase directly.
- Do not rewrite already-applied baseline migrations in place.
- Do not remove `business_id + environment` while adding `org_id`.
- Do not run live provider sends without explicit opt-in recipient flags.
- Preserve the existing dirty Supabase persistence work in `/Users/solomartin/Projects/Ares` until it is intentionally reconciled.

## Phase 0/1 verification

```bash
git diff --check
uv run pytest tests/smoke/test_health.py tests/api/test_runtime_config_contract.py tests/api/test_trigger_contract_files.py -q
npm --prefix trigger run typecheck
npm --prefix apps/mission-control run typecheck
```

## Next gate

Phase 2 starts only after Phase 0/1 is green and the uncommitted Supabase persistence slice in the original checkout is intentionally reconciled with this branch.
