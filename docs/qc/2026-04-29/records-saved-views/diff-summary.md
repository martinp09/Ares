# Diff Summary — Records Saved Views + 422 Warning Cleanup

## Backend API/runtime

- `app/main.py`
  - Adds a custom `RequestValidationError` handler that returns status `422` without using the deprecated FastAPI status alias.
  - Uses `jsonable_encoder` so validation `ctx.error` values such as `ValueError` are JSON-safe.
- `app/api/commands.py`, `app/api/hermes_tools.py`, `app/api/lead_machine.py`, `app/api/marketing.py`
  - Replaces deprecated `HTTP_422_UNPROCESSABLE_ENTITY` usage with `HTTP_422_UNPROCESSABLE_CONTENT`.
- `app/api/mission_control.py`
  - Adds `POST /mission-control/records/saved-views`.

## CRM Records saved views

- `app/models/crm_records.py`
  - Adds `CrmRecordSavedView`.
- `app/models/mission_control.py`
  - Adds saved-view API/response models and includes saved views in the Records response.
- `app/db/client.py`
  - Adds in-memory saved-view stores/reset state.
- `app/db/crm_records.py`
  - Adds saved-view upsert/list support for both in-memory and Supabase-backed modes.
- `app/services/mission_control_service.py`
  - Returns saved views from the Records read model.
  - Provides default saved views when none are persisted.
  - Adds saved-view upsert service method.
- `supabase/migrations/20260429184500_crm_record_saved_views.sql`
  - Creates tenant-scoped `crm_record_saved_views` table, policies, indexes, and update trigger.

## Frontend

- `apps/mission-control/src/lib/api.ts`
  - Adds saved-view type/mapping and `savedViews` on Records data.
- `apps/mission-control/src/lib/fixtures.ts`
  - Adds fixture saved views.
- `apps/mission-control/src/App.tsx`
  - Adds loading snapshot default for `savedViews`.
- `apps/mission-control/src/pages/RecordsPage.tsx`
  - Adds saved-view rail and applies saved-view filters before operator tabs.
- `apps/mission-control/src/pages/RecordsPage.test.tsx`
  - Updates tests for saved-view UI labels and scoped filtering expectations.

## Tests/docs

- `tests/api/test_mission_control.py`
  - Adds saved-view API/read-model coverage.
- `tests/db/test_crm_records_repository.py`
  - Adds repository saved-view regression coverage.
- `tests/db/test_crm_record_saved_views_schema.py`
  - Adds migration/schema coverage for saved views.
- `CONTEXT.md`, `memory.md`
  - Records current status, open work, and change-log entry.
- `docs/qc/2026-04-29/records-saved-views/*`
  - Captures QC report, test output, diff check, and this diff summary.
