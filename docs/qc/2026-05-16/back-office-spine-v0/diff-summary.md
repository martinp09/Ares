# Back Office Spine v0 Diff Summary

## Backend domain/API/store

- `app/models/deals.py`
  - Adds canonical deal domain models, enums, provider-gate defaults, promotion/stage/fire-list request/response models.
- `app/db/deals.py`
  - Adds deal repository over the control-plane store with idempotent upserts and detail/list helpers.
- `app/db/client.py`
  - Adds in-memory deal spine collections and reset behavior.
- `app/db/control_plane_store_supabase.py`
  - Adds deal spine runtime table hydration/persistence for Supabase-backed control-plane mode.
- `app/services/deal_promotion_service.py`
  - Adds lead-to-deal promotion, lane template child creation, audit/stage initialization, no-send invariant.
- `app/services/deal_stage_service.py`
  - Adds stage transition validation, document blockers, risk blockers, audit/stage events, manual override support.
- `app/services/deal_fire_list_service.py`
  - Adds fire-list read model for blockers, missing docs, stale deals, risks, and provider gates.
- `app/api/deals.py`
  - Adds protected `/deals` list/detail/fire-list/promote/stage endpoints.
- `app/main.py`
  - Mounts the deals router.

## Supabase migration

- `supabase/migrations/20260516011000_deal_spine_runtime.sql`
  - Adds `deal_records_runtime`, `deal_parties_runtime`, `deal_tasks_runtime`, `deal_document_requirements_runtime`, `deal_audit_events_runtime`, `deal_stage_events_runtime`, and `deal_risk_flags_runtime` tables plus indexes.

## Backend tests

- `tests/models/test_deals.py`
- `tests/db/test_deals_repository.py`
- `tests/db/test_deal_spine_schema.py`
- `tests/db/test_deal_supabase_persistence.py`
- `tests/services/test_deal_promotion_service.py`
- `tests/services/test_deal_stage_service.py`
- `tests/services/test_deal_fire_list_service.py`
- `tests/api/test_deals_api.py`

Coverage includes:

- no-send/provider-gate defaults;
- probate/curative-title and lease-option promotion templates;
- idempotent deal promotion;
- contact candidates not being confirmed sellers;
- stage blockers/manual override;
- fire-list generation;
- protected API contract;
- Supabase runtime table schema and mocked persistence/hydration.

## Mission Control frontend

- `apps/mission-control/src/lib/api.ts`
  - Adds typed Deal Desk read model/client mapping for `/deals` and `/deals/fire-list`.
- `apps/mission-control/src/lib/api.test.ts`
  - Adds client mapping coverage.
- `apps/mission-control/src/lib/fixtures.ts`
  - Adds Deal Desk fixture fallback.
- `apps/mission-control/src/App.tsx`
  - Adds Deal Desk under the Pipeline workspace and fetches deal read model with fixture fallback.
- `apps/mission-control/src/pages/DealDeskPage.tsx`
  - Adds read-only Deal Desk page with metrics, deal cards, and fire-list cards.
- `apps/mission-control/src/pages/DealDeskPage.test.tsx`
  - Adds page-level rendering coverage.
- `apps/mission-control/src/styles.css`
  - Adds Deal Desk layout/card styles.

## Docs/QC

- `CONTEXT.md`
- `TODO.md`
- `memory.md`
- `/root/obsidian-vault/03-Experiments/Ares Real Estate Operating System RPD.md`
- `docs/qc/2026-05-16/back-office-spine-v0/*`

Docs updated to reflect local implementation status, QC evidence, no-send guardrails, and remaining ship-clean step.
