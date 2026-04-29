# CRM Supabase Validation Diff Summary

## Code

- `app/db/crm_records.py`
  - Changed `CrmRecordsRepository` memory-forcing behavior so Supabase is used whenever `LEAD_MACHINE_BACKEND=supabase` is active unless `force_memory=True` is explicitly passed.
  - This fixes Mission Control CRM Records silently falling back to the memory path when the shared control-plane client is memory-backed.

## QC artifacts

- `docs/qc/2026-04-29/crm-supabase-validation/REPORT.md`
  - Scope, bug found/fixed, commands, results, and remaining notes.

- `docs/qc/2026-04-29/crm-supabase-validation/smoke-output.txt`
  - Local Supabase smoke output showing CRM Records/saved views/promotion/pipeline/stage-history persisted.

- `docs/qc/2026-04-29/crm-supabase-validation/test-output.txt`
  - Combined smoke output, focused pytest output, and `git diff --check` result.

## Validation evidence

The local Supabase smoke created and read back rows in:

- `crm_records`
- `crm_source_records`
- `crm_record_saved_views`
- `crm_record_status_history`
- `crm_record_promotions`
- `opportunities`
- `opportunity_pipeline_configs`
- `opportunity_stage_history`
