# Diff Summary — Records Action UI

## Frontend API client

- `apps/mission-control/src/lib/api.ts`
  - Adds record action request/result types.
  - Adds API methods for status update, suppression, and promotion endpoints.
  - Extracts `mapRecordSummary` for reuse by read and command responses.
  - Adds `mapRecordAction` for `/mission-control/records/*` command responses.

## Mission Control app wiring

- `apps/mission-control/src/App.tsx`
  - Adds Records action state.
  - Adds handlers for status update and suppression commands.
  - Optimistically replaces updated records, then clears the local query cache and refetches Records/dashboard.
  - Passes action handlers/state into `RecordsPage`.

## Records UI

- `apps/mission-control/src/pages/RecordsPage.tsx`
  - Adds row action buttons for mark marketable, needs skip trace, suppress, and promote gated.
  - Wires status/suppression callbacks when parent handlers are provided.
  - Keeps promotion disabled with explanatory title/copy until source identity is exposed.

## Styling

- `apps/mission-control/src/styles.css`
  - Adds ghost button styling for row actions.
  - Adds red status badge styling for command errors.

## Tests/docs/QC

- `apps/mission-control/src/pages/RecordsPage.test.tsx`
  - Updates assertions for real action controls and gated promotion.
- `CONTEXT.md`, `memory.md`
  - Updates recent changes and open work.
- `docs/qc/2026-04-29/records-action-ui/*`
  - Captures report, command output, and this summary.
