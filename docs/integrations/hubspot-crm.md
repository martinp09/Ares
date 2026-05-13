# HubSpot CRM integration

Status: current
Last verified: 2026-05-13

## Purpose

Ares can prepare a HubSpot CRM structure that fits the real-estate operator workflow without letting HubSpot become the source of truth.

Source of truth remains:
- Ares / Supabase for canonical records, tasks, title packets, provenance, and operator state.
- HubSpot for synced operator CRM views: people, property/opportunity deals, pipeline stages, and follow-up visibility.

## Secret handling

Do not commit HubSpot credentials.

Supported env names:

```env
HUBSPOT_ACCESS_TOKEN=
HUBSPOT_PERSONAL_KEY=
HUBSPOT_DEVELOPER_KEY=
HUBSPOT_BASE_URL=https://api.hubapi.com
HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false
HUBSPOT_DEFAULT_PIPELINE_ID=
HUBSPOT_DEFAULT_DEAL_STAGE_ID=
HUBSPOT_OWNER_ID=
```

Notes:
- `HUBSPOT_ACCESS_TOKEN` or `HUBSPOT_PERSONAL_KEY` is used as the bearer token for CRM API calls.
- `HUBSPOT_DEVELOPER_KEY` is accepted for environment inventory but is not used for CRM bearer requests.
- Live writes require both `PROVIDER_LIVE_SENDS_ENABLED=true` and `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`.
- If a token was pasted into chat, rotate it later before any public or shared deployment.

## API docs referenced

- HubSpot Contacts API: `/crm/v3/objects/contacts`
- HubSpot Objects API: `/crm/v3/objects/{objectType}`
- HubSpot Properties API: `/crm/v3/properties/{objectType}`
- HubSpot Pipelines API: `/crm/v3/pipelines/{objectType}`

## Ares-to-HubSpot model

HubSpot Contacts represent people:
- owner
- heir / family contact
- executor / administrator
- probate applicant
- attorney / legal rep
- tenant / occupant
- buyer
- vendor
- wrong number / unknown

HubSpot Deals represent the property/opportunity thread:
- property address
- mailing address
- county
- HCTax/county account
- probate case number
- estimated value
- delinquent tax amount and year count
- debt-to-value percentage
- title/probate/tax flags
- document-pull status
- next operator action

HubSpot custom properties are prefixed with `ares_` so they are easy to identify and safe to audit.

## Default deal pipeline

Ares prepares a HubSpot deal pipeline called `Ares Acquisition Pipeline` with these stages:

- Research / title packet
- Needs skiptrace
- Contact ready
- Reached / qualifying
- Seller or heir interested
- Title / legal review
- Offer drafted
- Under contract
- Closed won
- Closed lost / suppressed

The skiptrace stage is intentionally separate from contact-ready and title-review. Phones/emails do not make a lead title-ready.

## Runtime endpoints

Preview or apply HubSpot customization:

```bash
curl -X POST "<ares-runtime>/crm/hubspot/customization" \
  -H "Authorization: Bearer <runtime-api-key>" \
  -H "Content-Type: application/json" \
  -d '{"business_id":"limitless","environment":"prod","dry_run_only":true}'
```

Sync one Ares CRM record to HubSpot contact/deal payloads:

```bash
curl -X POST "<ares-runtime>/crm/hubspot/records/sync" \
  -H "Authorization: Bearer <runtime-api-key>" \
  -H "Content-Type: application/json" \
  -d @record-sync-request.json
```

Default behavior is dry-run. Dry-run returns the exact property, pipeline, contact, and deal payloads but does not call HubSpot.

## Live-write gate

Before writing to HubSpot:

1. Put the token in deployment env, not repo files.
2. Run dry-run customization and inspect payload.
3. Set:

```env
PROVIDER_LIVE_SENDS_ENABLED=true
HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true
```

4. Call `/crm/hubspot/customization` with `dry_run_only=false`.
5. Confirm the custom properties and pipeline in HubSpot.
6. Set `HUBSPOT_DEFAULT_PIPELINE_ID` and `HUBSPOT_DEFAULT_DEAL_STAGE_ID` from the created HubSpot pipeline before record sync.
7. Run one approved record sync first.

## Guardrails

- No HubSpot live write happens by default.
- No paid skiptrace or outreach is triggered by this integration.
- No HubSpot association writes are performed yet; Ares prepares contact/deal payloads first. Live association IDs should be added only after the portal schema is confirmed.
- HubSpot must not replace Ares as the canonical title/probate/task/audit store.
