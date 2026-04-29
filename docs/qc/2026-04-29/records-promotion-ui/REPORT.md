# Records Promotion UI QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

Finish the Records promotion slice by exposing source lead/contact identity through the canonical Records read model and enabling the Mission Control `Promote` row action only when that identity is available.

## Changes

- Added optional `source_lead_id` / `source_contact_id` fields to Mission Control record summaries and record-import requests.
- Persisted imported source identity into canonical record facts and source-membership metadata.
- Added CRM repository lookup for source memberships so canonical records can recover lead/contact identity even when facts/raw payload are missing.
- Mapped source identity into the Mission Control frontend API model.
- Enabled the Records row `Promote` action for non-promoted records with source identity; rows without identity stay disabled as `Promote gated`.
- Wired App-level promote handling to call the existing backend promotion command and refresh Records/dashboard state.
- Added backend and frontend regressions for source identity and promote gating.

## Verification

Captured in `test-output.txt`.

Commands run:

```bash
npm --prefix apps/mission-control run typecheck
npm --prefix apps/mission-control test -- --run src/App.test.tsx src/pages/RecordsPage.test.tsx src/lib/api.test.ts
uv run pytest tests/api/test_mission_control.py tests/db/test_crm_records_repository.py -q
git diff --check
```

Results:

- Mission Control typecheck: passed
- Mission Control focused tests: 34 passed
- Backend focused Mission Control/CRM repository tests: 35 passed
- Whitespace diff check: passed

## Risks / Notes

- Promotion source-lane selection currently derives from record source/type (`lease` -> `lease_option_inbound`, otherwise `probate`). This is acceptable for the current bounded CRM slice but should be revisited when source-lane metadata becomes explicit on canonical records.
- Supabase live validation for Records actions, saved views, and pipeline config remains a follow-up item.

## Remaining Work

1. Validate Records action API, saved views, and pipeline/stage config against Supabase.
2. Continue owner/property graph, research cockpit, and map UI only after Records and stage model stabilize.
