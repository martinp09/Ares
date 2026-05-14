# Diff Summary

## Local ignored changes
- `.env`
  - Replaced `HUBSPOT_ACCESS_TOKEN` with the short-lived OAuth access token exchanged from the new personal access key.
  - Replaced `HUBSPOT_PERSONAL_KEY` with the new personal access key.
  - Preserved `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`.
- `.env.before-hubspot-token-20260514T012600Z`
  - Local ignored backup before the token edit.

## Tracked artifacts
- `docs/qc/2026-05-14/hubspot-personal-key-setup/test-output.txt`
  - Sanitized refresh/probe evidence; no secret values.
- `docs/qc/2026-05-14/hubspot-personal-key-setup/REPORT.md`
  - Sanitized setup report; no secret values.

## Provider side effects
- Live HubSpot mutations: `0`.
