# Phase 6 Vapi Call Layer QC Report

Date: 2026-05-14

## Scope

Implemented Phase 6 Vapi voice call layer with dry-run outbound preview, gated live dispatch, webhook secret check, provider adapter, typed models, API routes, and fake-provider tests only.

## Fix-lane update

- Removed live Vapi outbound payload echo from dispatch, existing-link skip, submitted-unlinked, and error responses.
- Dry-run responses still return the full generated Vapi payload for operator preview.
- Live responses now return only a redacted payload summary with presence/count booleans; they do not include raw `to_number`, `customer_name`, assistant ID, phone number ID, or arbitrary metadata values.
- Added tests covering live success, submitted-unlinked, existing-link skip, and provider-error responses for payload redaction while preserving dry-run full payload behavior.
- Strengthened Vapi transport/error sanitization tests to assert configured API/private key values do not appear in sanitized error messages or headers.
- Aligned the stale planning env reference from the retired live-calls Vapi gate name to active `VAPI_PROVIDER_LIVE_SENDS_ENABLED`; repository search found no active config using the retired name.

## Safety posture

- No live Vapi provider calls were made.
- Tests use injected fake clients or API monkeypatching only.
- Live outbound calls are gated by all of:
  - `operator_approval=true`
  - `PROVIDER_LIVE_SENDS_ENABLED=true`
  - `VAPI_PROVIDER_LIVE_SENDS_ENABLED=true`
  - Vapi API key/private key configured
  - assistant ID present
  - phone number ID present
  - `to_number` present
- Webhook first pass supports `X-Vapi-Secret == VAPI_WEBHOOK_SECRET` when `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true`; otherwise returns `unverified_accepted` trust metadata.
- Provider object links are written only after fake-provider success with a returned call ID.
- Secrets/tokens are redacted from adapter reprs, transport errors, and response tests.

## Final blocker fix update

- Changed live outbound dispatch exception responses to return the fixed generic message `Vapi provider dispatch failed.` instead of raw or partially redacted provider/client exception text.
- Added regression coverage proving long `assistant_id`/`phone_number_id`/`to_number` prefixes from truncated `ProviderTransportError` messages do not leak into serialized error responses.
- Added regression coverage proving nested request metadata scalar values echoed by `RuntimeError` do not leak into serialized error responses.
- Dry-run preview remains unchanged and still returns the full generated Vapi payload.
- Existing preflight validation errors remain useful and continue to raise before any provider/client call.

## Verification commands

```bash
python -m pytest tests/providers/test_vapi.py tests/services/test_vapi_call_service.py tests/api/test_voice.py -q
```

Result: `29 passed in 5.00s`

```bash
python -m pytest tests/services/test_hubspot_mirror_service.py tests/services/test_instantly_enrollment_service.py tests/db/test_provider_links_repository.py -q
```

Result: `46 passed in 1.73s`

```bash
python -m pytest -q
```

Result: `734 passed in 26.78s`

```bash
git diff --check
```

Result: passed with no output.

## Artifact tracking note

This QC directory documents the Phase 6 Vapi call-layer scope only. The working tree already contains prior uncommitted Phase 1-5/provider-link and unrelated artifacts; this report does not claim ownership of those pre-existing changes.
