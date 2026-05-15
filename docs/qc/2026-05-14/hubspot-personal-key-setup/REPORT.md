# HubSpot Personal Key Setup Report

## Scope
- Accepted the operator-supplied HubSpot Personal Access Key from the screenshot.
- Exchanged the personal key through HubSpot `localdevauth` for an API-ready OAuth access token.
- Stored secrets only in ignored local `.env` files for `/opt/ares/Ares`, `/opt/ares/worktrees/ares-main`, and `/opt/ares/worktrees/ares-hubspot-crm-customization`.
- Ran read-only HubSpot CRM probes only.

## Secret hygiene
- Raw personal key and OAuth token were not printed to stdout, committed, or written to tracked docs.
- `.env` mode set to `0600` where written.
- Backup created before local env edit: `/opt/ares/Ares/.env.before-hubspot-token-20260514T012600Z`.
- Personal key fingerprint: SHA-256 prefix `3a8f59a5fc6d`, length `107`.
- OAuth token fingerprint: SHA-256 prefix `024c6ae67e60`, length `262`.

## Refresh result
- Refresh status: `200`.
- Hub ID present: `True`.
- Hub name present: `True`.
- Scope groups returned: `19`.
- Enabled features returned: `11`.

## Read-only probe result
- Direct HubSpot read-only endpoints: `4/5` succeeded.
- Ares main worktree settings/provider smoke loaded the token and read owners successfully.
- Deal pipeline read returned `403`: `User level OAuth token is not allowed for this endpoint.`
- Probe details are in `test-output.txt` and are sanitized.

## Live-write gate
- `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`.
- Live HubSpot mutations: `0`.

## Notes
- A HubSpot Personal Access Key is not itself the bearer token for normal CRM REST calls; it must be exchanged for an OAuth access token first.
- The exchanged OAuth token is short-lived; durable Ares runtime support should refresh from `HUBSPOT_PERSONAL_KEY` before live provider calls.
- The previous direct-bearer probe against the personal key was therefore misleading.
- Current key is enough for owner/contact/deal property/contact reads, but not for deal pipeline reads/writes with this user-level OAuth token.
