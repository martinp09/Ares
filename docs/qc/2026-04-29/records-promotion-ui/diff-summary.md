# Records Promotion UI Diff Summary

## Backend

- `app/models/mission_control.py`
  - Added source lead/contact identity to record summaries.
  - Added source lead/contact identity to record import requests.

- `app/services/mission_control_service.py`
  - Carries imported source identity into canonical record facts and source membership metadata.
  - Resolves source identity from facts, raw payload, then source memberships when building canonical record summaries.
  - Exposes lead-machine fallback lead IDs as `source_lead_id` for promotion eligibility.

- `app/db/crm_records.py`
  - Added `list_source_memberships(record_id)` for memory and Supabase-backed stores.

- `tests/api/test_mission_control.py`
  - Expanded import/status/suppress/promote regression coverage to assert source identity is exposed on imported and listed records.

## Mission Control Frontend

- `apps/mission-control/src/lib/api.ts`
  - Added `sourceLeadId` / `sourceContactId` to `CrmRecordSummary` and payload mapping.
  - Expanded `CrmRecordStatus` union to match backend status values.

- `apps/mission-control/src/pages/RecordsPage.tsx`
  - Added `onRecordPromote` prop.
  - Enables `Promote` only for non-promoted records with source lead/contact identity.
  - Keeps identity-less rows disabled as `Promote gated`.

- `apps/mission-control/src/pages/RecordsPage.test.tsx`
  - Added coverage proving promote is enabled only when source identity exists.

- `apps/mission-control/src/App.tsx`
  - Added promote handler that calls the backend record promotion endpoint, refreshes Records/dashboard state, and reports action status.

## QC Artifacts

- `docs/qc/2026-04-29/records-promotion-ui/REPORT.md`
- `docs/qc/2026-04-29/records-promotion-ui/diff-summary.md`
- `docs/qc/2026-04-29/records-promotion-ui/diff-check.txt`
- `docs/qc/2026-04-29/records-promotion-ui/diff-stat.txt`
- `docs/qc/2026-04-29/records-promotion-ui/test-output.txt`
