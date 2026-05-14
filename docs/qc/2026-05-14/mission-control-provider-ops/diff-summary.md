# Diff Summary

## Frontend
- `apps/mission-control/src/lib/api.ts`
  - Added typed Phase 8 provider read/preview client methods.
  - Tightened HubSpot customization preview, HubSpot record-sync preview, and Instantly enrollment preview request types to backend-supported fields only.
  - Added Vapi outbound preview dry-run enforcement.
- `apps/mission-control/src/lib/api.test.ts`
  - Added URL/body/no-live endpoint coverage for provider ops methods.
  - Updated provider preview example calls to omit unsupported `business_id`/`environment` scope fields and assert those fields are not sent.
- `apps/mission-control/src/components/ProviderOperationsPanel.tsx`
  - New pure props-only provider ops panel for HubSpot, Instantly, Vapi, and nightly source/brief status.
- `apps/mission-control/src/components/ProviderOperationsPanel.test.tsx`
  - Added render/no-button/no-live assertions.
- `apps/mission-control/src/pages/DashboardPage.tsx`
  - Renders fixture-backed provider ops panel.
- `apps/mission-control/src/pages/DashboardPage.test.tsx`
  - Asserts provider ops panel appears without live action controls.
  - Scopes numeric/status assertions to their summary cards so provider ops preview counts do not collide with dashboard counts.
- `apps/mission-control/src/App.tsx`
  - Restored Lead Machine / Agents as the default workspace/view.
  - Treats the added suppression fallback view as part of full fixture mode.
- `apps/mission-control/src/App.test.tsx`
  - Preserves agents-first org/scope assertions while allowing unrelated pipeline fallback labels in tests that do not mock pipeline reads.
  - Scopes duplicated pipeline stage text to stage headings.
- `apps/mission-control/src/lib/fixtures.ts`
  - Added provider ops fixture data.

## Backend / Hermes
- `app/services/command_service.py`
  - Added safe preview/read tool command names.
  - Added approval-required live/apply/dispatch command names.
- `app/services/hermes_tools_service.py`
  - Added payload schemas for provider ops tools.
- `tests/api/test_hermes_tools.py`
  - Added catalog assertions for safe preview/read tools and approval-gated live/apply names.

## Docs / memory
- Added Phase 8 QC artifacts under `docs/qc/2026-05-14/mission-control-provider-ops/`.
- Updated `CONTEXT.md` and `memory.md` with concise Phase 8 completion notes.
