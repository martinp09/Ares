# Diff Summary

## Added

- `apps/mission-control/src/components/ProbateAutopilotHealthPanel.tsx`
  - Read-only operator panel for probate autopilot health.
  - Shows SLA, freshness, no-send safety, source quality, enrichment backlog, anomaly watch, and next actions.
  - Surfaces aggregate duplicate counts by county only.

- `apps/mission-control/src/pages/ProbateAutopilotPage.tsx`
  - Thin page wrapper for the health panel.

- `apps/mission-control/src/pages/ProbateAutopilotPage.test.tsx`
  - Verifies the panel renders source-run SLA/backlog state.
  - Verifies no raw case number / owner name appears.
  - Verifies no scrape/sync/send/enroll/call/skiptrace button is rendered.

- `docs/qc/2026-05-15/probate-autopilot-mission-control-health-panel/`
  - QC report, diff summary, and command output evidence.

## Updated

- `apps/mission-control/src/App.tsx`
  - Added Lead Machine `Autopilot` nav item.
  - Fetches `GET /mission-control/probate-autopilot/health` through the existing query client.
  - Keeps optional probate-health fixture fallback from downgrading the whole shell data-source badge.
  - Adds context copy reinforcing the no-send intelligence gate.

- `apps/mission-control/src/lib/api.ts`
  - Added typed frontend model for probate autopilot health.
  - Added mapper from backend snake_case response into camelCase UI data.
  - Drops arbitrary raw payload fields and exposes only approved summary fields.

- `apps/mission-control/src/lib/api.test.ts`
  - Added redaction test proving raw case numbers, owner names, raw rows, and raw duplicate maps are not mapped into the UI model.
  - Preserved provider preview/read endpoint no-live-path assertions.

- `apps/mission-control/src/lib/fixtures.ts`
  - Added fixture health data for the Autopilot page.

## Not Changed

- No backend write paths.
- No provider client mutations.
- No Trigger schedule changes.
- No HubSpot/Instantly/SMS/Vapi/direct-mail/skiptrace activation.
