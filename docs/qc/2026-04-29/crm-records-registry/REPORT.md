# QC Report: CRM Records Registry

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Repo: `martinp09/Ares`

## Scope

Implemented the first canonical CRM Records registry foundation after the initial Mission Control Records read-model shell.

## Changes

- Added canonical CRM Records domain models:
  - `CrmRecord`
  - `CrmSourceRecord`
  - `CrmRecordSourceMembership`
  - `CrmRecordStatusHistory`
  - `CrmRecordPromotion`
- Added `CrmRecordsRepository` with memory and Supabase adapter paths for:
  - record upsert/list/get
  - source record upsert
  - source membership preservation
  - status history append/update
  - record promotion history
- Added Supabase migration `20260429180000_crm_records_registry.sql` for:
  - `crm_records`
  - `crm_source_records`
  - `crm_record_source_memberships`
  - `crm_record_status_history`
  - `crm_record_promotions`
- Wired Mission Control Records/dashboard read models to prefer canonical CRM records when present.
- Kept the existing lead-machine projection shell available for scopes with no canonical CRM records yet.
- Updated `CONTEXT.md` and `memory.md`.

## Verification

Captured in `test-output.txt`.

Passed:

- `git diff --check`
- `uv run pytest tests/db/test_crm_records_repository.py tests/db/test_crm_records_schema.py tests/api/test_mission_control.py -q`
  - `33 passed`
- `uv run pytest -q`
  - `593 passed, 6 warnings`
- `npm --prefix apps/mission-control run test -- --run src/pages/RecordsPage.test.tsx src/pages/DashboardPage.test.tsx`
  - `2 files passed / 3 tests passed`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run build`
- `npm --prefix trigger run typecheck` after `npm --prefix trigger ci`
- `uv lock --check`
- `uv run python -m compileall app`

## Notes / Risks

- Delegated subagent attempts failed because both Hermes delegation and direct Codex CLI lacked usable API authentication in this session. The failure is documented in the chat/session; implementation continued manually with the same scoped plan.
- The Records read model is canonical-first but still uses the existing lead-machine projection shell when no canonical records exist for a scope. This preserves current Mission Control visibility until imports populate canonical records.
- UI bulk actions, saved views, and actual import/promotion API command routes are intentionally deferred to the next slice.
- Trigger `npm ci` surfaced existing dependency audit warnings: 3 low, 1 moderate, 4 high. No typecheck blocker.
- Mission Control `npm ci` previously surfaced existing 6 moderate vulnerabilities. No test/typecheck/build blocker.
