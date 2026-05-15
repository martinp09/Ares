# HubSpot Service Key Smoke

- Timestamp: 2026-05-14T02:51:42Z
- Scope: configure the supplied HubSpot Service Key for Ares local REST API access and verify read-only CRM reachability.
- Docs read: HubSpot `Make API requests using a service key (BETA)` and developer-platform `Scopes` docs through the HubSpot MCP docs tool.

## Official-doc findings

- HubSpot Service Keys are public beta.
- Service Keys are created under **Development → Keys → Service keys**.
- Service Keys are configured with object-specific scopes such as `crm.objects.contacts.read`.
- Service Keys are used directly as REST API bearer tokens: `Authorization: Bearer <service-key>`.
- Service Keys cannot authenticate webhooks, calls within UI extensions, or other developer-platform app functionality beyond direct REST API requests.
- Service Keys are subject to privately-distributed app limits.

## Local env change

- Updated ignored local `/opt/ares/Ares/.env` only.
- Set `HUBSPOT_ACCESS_TOKEN` to the supplied Service Key.
- Preserved `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false`.
- Created ignored local backup: `.env.before-hubspot-service-key-20260514T025025Z`.
- `.env` mode: `0600`.
- Token value: redacted. Sanitized fingerprint: `e42458734c62`, length `44`, prefix class `pat-na2`.

## Read-only probe results

See `probe-output.txt` for sanitized raw evidence.

Summary:

- Owners list: HTTP 200.
- Contacts object list: HTTP 200.
- Companies object list: HTTP 200.
- Deals object list: HTTP 200.
- Contact properties: HTTP 200, 386 properties returned.
- Company properties: HTTP 200, 257 properties returned.
- Deal properties: HTTP 200, 212 properties returned.
- Deal pipelines via `/crm/v3/pipelines/deals`: HTTP 200.
- Deal pipelines via `/crm/pipelines/2026-03/deals`: HTTP 200.

## Safety / side effects

- Live HubSpot writes: `0`.
- Contact creates/updates: `0`.
- Company creates/updates: `0`.
- Deal creates/updates: `0`.
- Property creates/updates: `0`.
- Pipeline creates/updates: `0`.
- Provider live-write gate remains disabled.

## Interpretation

The Service Key is sufficient for the current Ares REST/API integration path. It resolved the previous user-level OAuth limitation for read-only deal pipeline access. Because the key was pasted into chat, rotate it before shared/public production use if this transcript or logs are exposed outside the trusted operator environment.
