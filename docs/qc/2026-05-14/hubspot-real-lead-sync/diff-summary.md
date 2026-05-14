# HubSpot Real Lead Sync Diff Summary

## Files changed in this slice

- `docs/qc/2026-05-14/hubspot-real-lead-sync/REPORT.md`
  - Documents the HubSpot-only real-lead sync, side-effect scope, readback IDs, and follow-up gates.
- `docs/qc/2026-05-14/hubspot-real-lead-sync/test-output.txt`
  - Captures dry-run preview, gated live apply, provider-link verification, and HubSpot readback output.
- `docs/qc/2026-05-14/hubspot-real-lead-sync/diff-summary.md`
  - This summary.

## Living-doc updates

- `docs/qc/2026-05-14/README.md`
  - Added the real-lead HubSpot sync slice and updated live-side-effect posture.
- `CONTEXT.md`
  - Added the real-lead sync status, QC path, and Instantly copy/warmup follow-up.
- `TODO.md`
  - Added the real-lead sync status and future Instantly copy/approval gate.
- `README.md`
  - Added the real-lead sync status and QC path.
- `memory.md`
  - Added current-direction and change-log entries for the real-lead sync.

## Code changes

None. This was a live provider smoke/sync slice using the existing gated HubSpot record-sync service path.

## Live side effects

- Created one HubSpot contact and one HubSpot deal for `lead_341`.
- Created provider links `plink_3` and `plink_4`.
- No Instantly, Reacher, Vapi, source-provider, Slack, or deploy side effects.
