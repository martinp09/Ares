# Diff Summary: Opportunity Pipeline Config

## Modified

- `app/models/opportunities.py`
  - Added `OpportunityPipelineStageConfig`, `OpportunityPipelineConfig`, and `OpportunityStageHistoryRecord`.
  - Added validation for unique pipeline stage keys and stage orders.

- `app/db/opportunities.py`
  - Added repository methods for pipeline config upsert/list/lookup.
  - Added repository methods for stage history append/list.
  - Added Supabase mapping for `opportunity_pipeline_configs` and `opportunity_stage_history`.

- `app/services/opportunity_service.py`
  - Replaced hardcoded stage-rank map with active pipeline config lookup and default config fallback.
  - Added stage history writes when stage transitions occur.
  - Exposed pipeline config and stage history service methods.

- `app/db/client.py`
  - Added in-memory store/reset state for pipeline configs and stage history.

- `tests/services/test_opportunity_service.py`
  - Added configurable pipeline order/history coverage.
  - Added unconfigured-stage rejection coverage.

- `tests/db/test_opportunities_repository.py`
  - Added repository coverage for pipeline config upsert/list and stage history append/list.

- `CONTEXT.md`
  - Updated current TODO and recent changes.

- `memory.md`
  - Updated open work and change log.

## Added

- `supabase/migrations/20260429183000_opportunity_pipeline_config.sql`
  - Adds `opportunity_pipeline_configs` and `opportunity_stage_history` tables with tenant RLS.

- `tests/db/test_opportunity_pipeline_schema.py`
  - Checks the pipeline config migration contains tables, constraints, RLS policies, and trigger wiring.

- `docs/qc/2026-04-29/opportunity-pipeline-config/REPORT.md`
- `docs/qc/2026-04-29/opportunity-pipeline-config/diff-summary.md`
- `docs/qc/2026-04-29/opportunity-pipeline-config/test-output.txt`
