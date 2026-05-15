# Instantly Creation Attempt — 2026-05-02

## Goal

Create two draft cold-email campaigns in Instantly if API access allowed:

1. `Email | Probate | Inherited Property Relief Plan | Texas | 2026-05`
2. `Email | Tax + Title Friction | Property Situation Review | Texas | 2026-05`

## Preflight result

- `INSTANTLY_API_KEY` exists in `/opt/ares/Ares/.env`.
- Secret was not printed or stored.
- API preflight endpoint: `GET https://api.instantly.ai/api/v2/campaigns?limit=1`.
- Response: `HTTP 403`, body `error code: 1010`.

## Interpretation

The local host is blocked by Instantly/Cloudflare signature policy before campaign creation can be attempted. This matches the earlier Instantly smoke-test blocker.

## Safety decision

No live sends were attempted.
No campaign activation was attempted.
No recipient lists were uploaded.

## Local backups created

- `docs/marketing/campaigns/2026-05-02-probate-cold-email-professional-service-campaign.md`
- `docs/marketing/campaigns/2026-05-02-tax-curative-title-cold-email-professional-service-campaign.md`
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/cold-email-campaigns.json`
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/sequence-import-backup.csv`

## Next options

1. Create the campaigns manually in Instantly using the local backup docs/CSV.
2. Retry API creation from an allowed/residential/admin environment.
3. Add an Ares-side campaign export/import UI so operator can copy exact sequence steps into Instantly.
