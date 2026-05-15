# QC Report — Cold Email Campaign Packets

## Scope

Created full professional-service-style cold email campaign packets for:

1. Probate / inherited property sellers.
2. Tax delinquent / curative-title / property-friction owners.

The campaigns apply the Ares copy brain doctrine:

- Hormozi offer-first architecture.
- Alen Sultanic copy hinge.
- Recency + Relevance + Personalization.
- Offer-code / Rosetta Stone language.
- REI multichannel playbook rules.
- SMS is consent/inbound only.

## Local outputs

- `docs/marketing/campaigns/2026-05-02-probate-cold-email-professional-service-campaign.md`
- `docs/marketing/campaigns/2026-05-02-tax-curative-title-cold-email-professional-service-campaign.md`
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/cold-email-campaigns.json`
- `docs/marketing/exports/instantly-campaign-backups-2026-05-02/sequence-import-backup.csv`

## Content included

Each campaign includes:

- high-level offer and positioning
- segment rules
- required variables
- deliverability/compliance settings
- 4-step active cold email cadence
- long nurture cadence through day 300 and quarterly thereafter
- reply handling snippets
- compliance footer

## Instantly status

Instantly API preflight was attempted with the configured API key present in `.env` without exposing the secret.

Result:

- `GET /api/v2/campaigns?limit=1`
- `HTTP 403`
- body: `error code: 1010`

No campaigns were created in Instantly from this host because the API is blocked by provider/Cloudflare policy. Local backups are ready for manual entry/import or retry from an allowed environment.

## Safety

- No live sends.
- No lead uploads.
- No campaign activation.
- No SMS cold-prospecting copy created as a sendable sequence.
- Tax/title copy avoids shaming delinquency and avoids legal/tax advice.
- Probate copy avoids courthouse-vulture language.
