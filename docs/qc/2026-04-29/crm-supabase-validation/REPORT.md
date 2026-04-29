# CRM Supabase Validation QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

Validate the CRM Records action API, saved views, promotion path, and opportunity pipeline/stage config against a real local Supabase stack instead of only in-memory repository tests.

## What was validated

A local Supabase stack was started and migrations applied through:

- `20260429180000_crm_records_registry.sql`
- `20260429183000_opportunity_pipeline_config.sql`
- `20260429184500_crm_record_saved_views.sql`

The smoke exercised:

1. Create tenant business through Supabase REST.
2. Create source lead through Supabase REST.
3. Create CRM record saved view through Mission Control API.
4. Import canonical CRM record with `source_lead_id` through Mission Control API.
5. Update CRM record status to `marketable` through Mission Control API.
6. List Records and verify saved view + source identity survive readback.
7. Promote CRM record into an opportunity through Mission Control API.
8. Upsert configurable opportunity pipeline config through `OpportunityService`.
9. Advance opportunity stage and persist stage history.
10. Count rows in the relevant Supabase tables.

## Bug found and fixed

The first Supabase smoke showed CRM Records were silently using the in-memory path inside `MissionControlService` even when `LEAD_MACHINE_BACKEND=supabase` was set.

Root cause:

- `MissionControlService` passes its shared control-plane client into `CrmRecordsRepository`.
- That client is normally memory-backed unless `CONTROL_PLANE_BACKEND=supabase` is also enabled.
- `CrmRecordsRepository` treated any non-Supabase client as an implicit `force_memory=True`, which overrode the lead-machine Supabase backend setting.

Fix:

- `CrmRecordsRepository` now only forces memory when `force_memory=True` is explicitly passed.
- This preserves explicit memory tests while allowing CRM Records to use Supabase when `LEAD_MACHINE_BACKEND=supabase` is active.

## Verification

Captured in `test-output.txt`.

Commands/results:

- Local Supabase CRM smoke: passed
- `uv run pytest tests/api/test_mission_control.py tests/db/test_crm_records_repository.py -q`: `35 passed`
- `git diff --check`: passed

Smoke row counts for the validated tenant:

- `crm_records`: 1
- `crm_source_records`: 1
- `crm_record_saved_views`: 1
- `crm_record_status_history`: 3
- `crm_record_promotions`: 1
- `opportunities`: 1
- `opportunity_pipeline_configs`: 1
- `opportunity_stage_history`: 1

## Notes

- No remote Supabase project was linked in this worktree (`supabase/.temp/project-ref` and `supabase/.temp/pooler-url` were missing), so this validation was local Supabase only.
- The local Supabase CLI output includes a harmless notice about stopped optional services and a newer CLI version being available.
- The smoke uses local default Supabase keys only; no production secrets are included in artifacts.

## Remaining Work

1. If remote validation is needed, link or provide the intended Supabase project ref/DB credentials first, then run a dry-run/apply workflow against that explicit target.
2. Add explicit canonical source-lane metadata for CRM records before expanding promotion routing beyond the current probate/lease-option heuristic.
