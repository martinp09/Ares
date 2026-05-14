# Diff Summary — HubSpot Service Key Smoke

## Local ignored env

- `/opt/ares/Ares/.env`
  - Set `HUBSPOT_ACCESS_TOKEN` to the supplied HubSpot Service Key.
  - Forced/preserved `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`.
  - Created backup `.env.before-hubspot-service-key-20260514T025025Z`.
  - No secret value recorded in this artifact.

## Tracked repo files

- `.env.example`
  - Added a non-secret comment clarifying that `HUBSPOT_ACCESS_TOKEN` can be a HubSpot Service Key (`pat-na*`) or a Private App access token.

- `docs/qc/2026-05-14/hubspot-service-key-smoke/`
  - Added sanitized docs/probe evidence for the Service Key setup.

## External systems

- HubSpot API read-only checks only.
- No HubSpot mutations were performed.
