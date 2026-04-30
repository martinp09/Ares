# Records Bulk Actions Diff Summary

## Frontend UI

- `apps/mission-control/src/pages/RecordsPage.tsx`
  - Adds selected-record state.
  - Adds row-level selection checkboxes and select-visible control.
  - Adds a bulk action toolbar for selected visible records.
  - Disables bulk controls when no visible records are selected or an action is running.
  - Bulk actions call existing real command callbacks for status updates and suppression.
  - Keeps promote gating unchanged.

- `apps/mission-control/src/App.tsx`
  - Passes async record status/suppress/promote handlers directly so bulk fanout can await existing callbacks.

- `apps/mission-control/src/pages/RecordsPage.test.tsx`
  - Adds focused coverage for visible-only bulk status/suppress fanout.
  - Adds disabled-state coverage for no selection and running action state.
  - Preserves existing coverage for KPIs, saved-view/tab filtering, and promotion gating.

- `apps/mission-control/src/styles.css`
  - Adds compact bulk-action and selection-row styling.

## Docs/QC

- `docs/qc/2026-04-29/records-bulk-actions/`
  - Captures QC report, diff summary, test output, and diff snapshots.
- `CONTEXT.md`, `memory.md`
  - Updates current open work and changelog with the bulk-action slice.
