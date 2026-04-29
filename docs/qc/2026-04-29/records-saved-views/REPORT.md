# Records Saved Views + 422 Warning Cleanup QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

This slice finishes the CRM Records saved views foundation and removes the backend 422 deprecation warnings that were polluting full-suite verification.

## Changes

- Added persisted CRM record saved views scoped by `business_id`, `environment`, and `slug`.
- Added Supabase migration `20260429184500_crm_record_saved_views.sql` for `crm_record_saved_views` with tenant scoping, RLS, default-view index, and updated-at trigger.
- Extended `CrmRecordsRepository` with in-memory and Supabase saved-view upsert/list paths.
- Added `POST /mission-control/records/saved-views` and included `saved_views` in `/mission-control/records` responses.
- Added default saved views when no persisted views exist: All records, Needs skip trace, Marketable, Promoted.
- Added Mission Control Records saved-view rail and frontend API/fixture/test coverage.
- Replaced deprecated `HTTP_422_UNPROCESSABLE_ENTITY` constants with `HTTP_422_UNPROCESSABLE_CONTENT`.
- Added a JSON-safe `RequestValidationError` handler in `app/main.py` so validation errors serialize cleanly and avoid FastAPI's deprecated 422 constant path.

## Verification

Captured in `test-output.txt`:

- `uv run pytest tests/api/test_mission_control.py tests/db/test_crm_records_repository.py tests/db/test_crm_record_saved_views_schema.py -q -W error::DeprecationWarning` → `36 passed`
- `uv run pytest tests/api/test_agents.py::test_create_agent_rejects_non_draft_lifecycle_status tests/api/test_ares_plans.py::test_ares_plans_route_rejects_whitespace_only_goal tests/api/test_lead_machine.py::test_post_probate_intake_rejects_missing_required_record_fields tests/api/test_skills.py::test_skill_api_rejects_blank_skill_metadata_entries -q -W error::DeprecationWarning` → `4 passed`
- `uv run pytest -q -W error::DeprecationWarning` → `602 passed`
- `uv run python -m compileall app` → passed
- `npm --prefix apps/mission-control run typecheck` → passed
- `npm --prefix apps/mission-control test -- RecordsPage.test.tsx --run` → `2 passed`
- `git diff --check` → passed, captured in `diff-check.txt`

## Risks / Notes

- Saved views are now API-backed, but live Supabase validation is still pending for the broader Records action API, saved views, and pipeline/stage config set.
- Mission Control saved-view creation UI is not added yet; this slice wires persisted views, response shape, defaults, and read-side saved-view filtering.
- Records write buttons should remain cautious until the live Supabase validation step is complete.

## Result

PASS. The saved-views slice and 422 warning cleanup are locally verified and ready to commit/push.
