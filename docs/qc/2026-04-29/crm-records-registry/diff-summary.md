# Diff Summary: CRM Records Registry

## Added

- `app/models/crm_records.py`
  - Canonical CRM record/source/membership/status/promotion Pydantic models and enums.
- `app/db/crm_records.py`
  - Memory + Supabase repository for canonical Records registry operations.
- `supabase/migrations/20260429180000_crm_records_registry.sql`
  - Tenant-scoped CRM registry tables, constraints, RLS, policies, triggers, and indexes.
- `tests/db/test_crm_records_repository.py`
  - Supabase adapter and memory promotion/status regression coverage.
- `tests/db/test_crm_records_schema.py`
  - Migration/schema contract checks.
- `docs/qc/2026-04-29/crm-records-registry/`
  - Durable verification artifacts for this slice.

## Modified

- `app/db/client.py`
  - Added in-memory store dictionaries for CRM records, source records, memberships, status history, and promotions.
- `app/services/mission_control_service.py`
  - Injected `CrmRecordsRepository`.
  - Made `/mission-control/records` and dashboard inventory canonical-first when CRM records exist.
  - Added canonical CRM record summary/KPI builders.
- `tests/api/test_mission_control.py`
  - Added Mission Control regression proving canonical CRM records are preferred and scoped correctly.
- `CONTEXT.md`
  - Updated current TODO/recent change for the canonical Records slice.
- `memory.md`
  - Added durable changelog and refreshed open work.

## Not Changed

- No direct Mission Control frontend Supabase access.
- No live provider wiring.
- No pipeline/stage schema changes yet.
- No owner/property/contact graph yet.
