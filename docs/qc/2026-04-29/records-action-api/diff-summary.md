# Diff Summary: Records Action API

## Modified

- `app/models/mission_control.py`
  - Added Records action request/response schemas for import, status update, suppression, and promotion.

- `app/api/mission_control.py`
  - Added Mission Control Records action endpoints.
  - Maps missing records to `404` and promotion contract violations to `422`.

- `app/services/mission_control_service.py`
  - Added import/status/suppress/promote service methods.
  - Import path upserts source records, canonical records, source memberships, and status history.
  - Promotion path creates/links opportunities and records promotion lineage.

- `app/db/crm_records.py`
  - Hardened Supabase promotion insert path with existing-row lookup before insert.

- `tests/api/test_mission_control.py`
  - Added API regression coverage for import -> status -> suppress -> promote.
  - Added repeated-promotion idempotency coverage.
  - Added validation coverage for missing/ambiguous promotion identities.

- `CONTEXT.md`
  - Updated current TODO and recent change status after action API implementation.

- `memory.md`
  - Updated open work and change log for action API completion.

## Added

- `docs/qc/2026-04-29/records-action-api/REPORT.md`
- `docs/qc/2026-04-29/records-action-api/diff-summary.md`
- `docs/qc/2026-04-29/records-action-api/test-output.txt`
