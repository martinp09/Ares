# QC Report: Opportunity Pipeline Config

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Repo: `martinp09/Ares`

## Scope

Added the configurable opportunity pipeline/stage foundation that follows the Records action API and promotion path.

## Changes

- Added opportunity pipeline config models scoped by business, environment, and source lane.
- Added ordered pipeline stage config entries with labels, ordering, terminal markers, and metadata.
- Added opportunity stage history records for auditable stage transitions.
- Extended `OpportunitiesRepository` with in-memory and Supabase paths for pipeline configs and stage history.
- Updated `OpportunityService.advance_stage` to use configured stage order and terminal-stage semantics instead of a hardcoded rank map.
- Added Supabase migration `20260429183000_opportunity_pipeline_config.sql` for:
  - `opportunity_pipeline_configs`
  - `opportunity_stage_history`
  - RLS policies
  - indexes
  - `touch_updated_at` trigger for pipeline configs
- Updated living docs for current TODOs and change log.

## Verification

Captured in `test-output.txt`:

- `git diff --check` — passed
- Focused opportunity pipeline tests — `12 passed`
- Mission Control/opportunity regression set — `51 passed`
- Full backend test suite — `600 passed, 6 warnings`
- `uv run python -m compileall app` — passed
- `npm --prefix apps/mission-control run typecheck` — passed

## Known Warnings

The full backend suite still reports six pre-existing FastAPI/AnyIO deprecation warnings around `HTTP_422_UNPROCESSABLE_ENTITY`. They are unchanged by this slice.

## Remaining Gaps

- Live Supabase migration/application smoke has not been run in this slice.
- No Mission Control UI editor for pipeline config yet; this slice establishes the backend model/repository/service/migration foundation.
- Records saved views remain the next product slice once filter semantics are stable.
