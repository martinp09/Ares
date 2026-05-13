# Diff Summary: HubSpot CRM Customization

## Runtime/API

- `app/api/hubspot_crm.py`
  - New protected HubSpot customization and record-sync endpoints.
- `app/main.py`
  - Registers HubSpot CRM router under runtime auth.

## Models/services/providers

- `app/models/hubspot_crm.py`
  - Pydantic models for HubSpot property definitions, pipeline specs, customization requests, record-sync requests, and provider action responses.
- `app/services/providers/hubspot.py`
  - HubSpot REST client for CRM properties, pipelines, search, object create/update, and idempotent object/property upsert helpers.
- `app/services/hubspot_crm_service.py`
  - Ares-specific HubSpot customization payload builder and dry-run/live-gated sync service.

## Config/env

- `app/core/config.py`
  - Adds HubSpot token, developer-key, base URL, live-write gate, default pipeline/stage, and owner ID settings.
- `.env.example`
  - Adds HubSpot placeholders only; no secrets.

## Tests

- `tests/providers/test_hubspot.py`
  - Authenticated request shape, property update fallback, and missing-token guard.
- `tests/services/test_hubspot_crm_service.py`
  - Dry-run customization, live-write gate, record-to-contact/deal mapping, and pipeline stage separation.
- `tests/api/test_hubspot_crm.py`
  - Protected API dry-run contracts for customization and record sync.

## Docs/QC

- `docs/integrations/hubspot-crm.md`
  - Operator runbook, env contract, model mapping, pipeline stages, live-write gate, and guardrails.
- `CONTEXT.md`
  - Updates current branch/scope/TODO.
- `memory.md`
  - Adds durable architecture/change-log entry and open work.
- `docs/qc/2026-05-13/hubspot-crm-customization/`
  - QC report, test output, and this diff summary.
