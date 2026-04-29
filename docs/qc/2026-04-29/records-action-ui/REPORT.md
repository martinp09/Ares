# Records Action UI QC Report

Date: 2026-04-29
Branch: `feature/ares-crm-control-plane-planning`
Worktree: `/opt/ares/worktrees/ares-crm-control-plane-planning`

## Scope

Wire Mission Control Records row controls to the real CRM command API where the backend contract is already safe, while keeping promotion gated until Records rows expose source lead/contact identity.

## Changes

- Added Mission Control frontend API methods for:
  - `POST /mission-control/records/{record_id}/status`
  - `POST /mission-control/records/{record_id}/suppress`
  - `POST /mission-control/records/{record_id}/promote`
- Added shared frontend record-action payload/result mapping.
- Added Records row action controls:
  - Mark marketable
  - Needs skip trace
  - Suppress
  - Promote gated
- Wired status/suppression buttons through `App.tsx` to real API calls.
- Added optimistic updated-record replacement plus Records/dashboard refetch after each successful command.
- Kept promotion disabled in the UI because backend promotion requires exactly one of `lead_id` or `contact_id`, and canonical Records rows do not yet expose that source identity.
- Updated CSS for ghost action buttons and error action badges.
- Updated Records page regression tests for the action controls and gated promotion state.
- Updated `CONTEXT.md` and `memory.md` to make the remaining source-identity/promotion work explicit.

## Verification

Captured in `test-output.txt`:

- `npm --prefix apps/mission-control run typecheck` → passed
- `npm --prefix apps/mission-control test -- --run src/App.test.tsx src/pages/RecordsPage.test.tsx src/lib/api.test.ts` → `33 passed`
- `uv run pytest tests/api/test_mission_control.py -q` → `33 passed`
- `git diff --check` → passed

## Risks / Notes

- Status and suppression are wired to real backend commands.
- Promotion API client support exists, but the visible row action remains gated until Records read models include the source `lead_id` or `contact_id` required by backend promotion validation.
- Live Supabase validation remains a separate step for Records actions, saved views, and pipeline/stage config.

## Result

PASS. Records action UI wiring is verified locally and ready to commit/push.
