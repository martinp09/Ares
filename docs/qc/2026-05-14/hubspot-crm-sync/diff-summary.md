# Diff Summary

## Phase 4 scope implemented

- Added gated HubSpot CRM record apply endpoint:
  - `POST /mission-control/providers/hubspot/records/apply-sync`
  - Requires `operator_approval`, `business_id`, `environment`, and typed record sync items.
- Added response schemas summarizing provider, live-applied status, created/updated/skipped/failed/error counts, per-object results, provider link IDs, provider object IDs, sync hashes, and warnings.
- Extended the HubSpot provider client with `update_object(...)` using `PATCH /crm/v3/objects/{objectType}/{recordId}` while preserving existing transport sanitization.
- Added `HubSpotMirrorService.apply_record_sync(...)` with the same live-write gate order as customization apply:
  1. operator approval
  2. global provider live gate
  3. HubSpot live gate
  4. token
- Reused the dry-run payload builders for live plans so preview/apply payload construction stays aligned.
- Implemented provider-link driven create/update logic:
  - contact records map to HubSpot contacts and `ares_object_type='crm_record'`.
  - entity records map to HubSpot companies and `ares_object_type='crm_record'`.
  - deals map to `ares_object_type='opportunity'` when `opportunity_id` is present, otherwise `crm_record`.
  - existing links update HubSpot objects through the fake client in tests.
  - missing links create HubSpot objects through the fake client and upsert provider links.
- Empty record apply returns zero counts plus warning, with no provider call and no link write.
- Associations are intentionally not added in Phase 4.

## Fix lane changes

- Added provider-level idempotency guard in `apply_record_sync`: when an existing HubSpot provider link has the same non-empty `sync_hash` as the incoming record plan, the service returns `action='skip'`, increments `skipped_count`, and avoids both HubSpot update calls and provider-link writes.
- Added a safe service-level error sanitizer for live-capable record sync results; fake client/repository exception text containing `Authorization`, `Bearer`, token values, secret query parameters, and API keys is redacted before being returned.
- Limited the no-email/no-phone contact matching warning to contact sync, so entity/company records without email/phone no longer warn.
- Updated operator-approval preflight text to reference HubSpot live writes/record sync rather than customization apply only.
- Strengthened the API no-secret regression to inspect serialized response body text.

## Files modified for this fix lane

- `app/services/hubspot_mirror_service.py`
- `tests/services/test_hubspot_mirror_service.py`
- `tests/api/test_hubspot_mirror.py`
- `docs/qc/2026-05-14/hubspot-crm-sync/REPORT.md`
- `docs/qc/2026-05-14/hubspot-crm-sync/diff-summary.md`
- `docs/qc/2026-05-14/hubspot-crm-sync/test-output.txt`

## Verification

- Required focused suite: `52 passed in 2.58s`.
- Full backend suite: `684 passed in 20.47s`.
- `git diff --check`: passed with no output.

## Safety notes

- No live HubSpot calls were made.
- No real provider writes were made.
- No tokens or secrets were added to code, tests, or QC artifacts.
