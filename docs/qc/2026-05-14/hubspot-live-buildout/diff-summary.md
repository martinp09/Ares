# Diff Summary

## Added / updated for HubSpot live buildout

- `app/services/hubspot_mirror_service.py`
  - Added a HubSpot single-pipeline fallback: when the portal already has one non-Ares pipeline and cannot create another, reuse the existing pipeline and add missing Ares stages.
  - Carries a warning into the apply response so the operator can see why `Sales Pipeline` was reused.

- `tests/services/test_hubspot_mirror_service.py`
  - Added regression coverage for single-pipeline portal reuse.

- `docs/qc/2026-05-14/hubspot-live-buildout/`
  - Added live buildout QC evidence and sanitized command output.

## Expected staged-doc follow-up

Update the QC index and living docs so they no longer claim “no live HubSpot writes” as the current repo state. The previous no-live final readiness folder remains valid historical evidence before the operator explicitly requested live HubSpot buildout.

## Excluded

- No raw HubSpot tokens or CRM row data.
- No record sync payloads.
- No Instantly, Vapi, source-provider, Slack, deploy, audit, or provider-send changes.
