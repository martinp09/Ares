# HubSpot Customization Apply Phase 3 QC

## Scope

Implemented Phase 3 code-only HubSpot customization live-apply command path with fake-client tests only. No real HubSpot writes, real provider sends, or live token usage were performed.

## Safety guardrails verified

- Apply command requires explicit `operator_approval=true`.
- Apply command fails before provider/client write calls unless `PROVIDER_LIVE_SENDS_ENABLED=true`.
- Apply command fails before provider/client write calls unless `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`.
- Apply command fails before provider/client write calls unless `HUBSPOT_ACCESS_TOKEN` is present.
- Preview routes remain dry-run/payload-only by default and do not call HubSpot.
- Tests use injected/fake HubSpot clients only for write behavior.
- Responses and tests do not expose provider tokens.

## Commands and results

- `python -m pytest tests/providers/test_hubspot.py -q`
  - Result: `8 passed in 0.98s`
- `python -m pytest tests/providers/test_hubspot.py tests/api/test_hubspot_mirror.py tests/services/test_hubspot_mirror_service.py -q`
  - Result: `30 passed in 1.60s`

- `python -m pytest tests/services/test_hubspot_mirror_service.py tests/api/test_hubspot_mirror.py tests/providers/test_hubspot.py -q`
  - Result: `29 passed in 1.57s`
- `python -m pytest tests/db/test_provider_links_repository.py tests/db/test_provider_links_schema.py tests/db/test_provider_links_supabase_adapter.py -q`
  - Result: `21 passed in 0.27s`
- `python -m pytest -q`
  - Result: `670 passed in 19.23s`
- `git diff --check`
  - Result: passed with no output

## Implementation summary

- Added `PROVIDER_LIVE_SENDS_ENABLED` global live-send gate, default false.
- Added Mission Control apply request/response schemas and `POST /mission-control/providers/hubspot/customization/apply`.
- Added idempotent HubSpot customization apply service logic:
  - reads existing property groups/properties/pipelines;
  - creates missing property groups/properties only;
  - creates the `Ares Acquisitions` pipeline with stages when absent;
  - uses an existing pipeline by label and creates only missing stages by label;
  - never deletes/replaces existing pipelines/stages.
- Extended HubSpot client with property-group list and pipeline-stage create helpers.
- Polished retry delay metadata handling so sanitized `Retry-After` headers are honored case-insensitively, including lowercase `retry-after`.
- Added fake-client service tests and API gate tests.

## Final status

Green. Phase 3 code/tests are implemented without live HubSpot writes.