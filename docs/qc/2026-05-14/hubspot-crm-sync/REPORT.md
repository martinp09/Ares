# HubSpot CRM Sync Phase 4 QC

## Scope

Implemented Phase 4 gated HubSpot CRM record/opportunity sync using provider links, then completed the REQUEST_CHANGES fix lane for record-sync idempotency and safe error reporting.

## Safety gates

- Record apply endpoint requires explicit operator approval.
- Live apply fails before provider calls and before provider-link writes unless all preflight gates pass:
  1. `operator_approval=true`
  2. `PROVIDER_LIVE_SENDS_ENABLED=true`
  3. `HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true`
  4. `HUBSPOT_ACCESS_TOKEN` present
- Dry-run preview remains token-free and never calls the provider or writes provider links.
- Tests use fake/injected HubSpot clients and in-memory provider-link repositories only.
- No live HubSpot calls or real provider writes were made.

## Implemented behavior

- Added `POST /mission-control/providers/hubspot/records/apply-sync`.
- Live apply uses provider links to choose create vs update.
- New HubSpot objects create provider object links with correct Ares object identity:
  - contact/company: `ares_object_type='crm_record'`, `ares_object_id=record.id`
  - deal with opportunity: `ares_object_type='opportunity'`, `ares_object_id=opportunity_id`
  - deal without opportunity: `ares_object_type='crm_record'`, `ares_object_id=record.id`
- Existing provider links update HubSpot objects rather than creating duplicates when the incoming `sync_hash` is empty or changed.
- Existing provider links with the same non-empty incoming `sync_hash` skip the provider update, increment `skipped_count`, and avoid provider-link mutation.
- Live-capable per-record errors are sanitized before returning service results, including fake client/repository exception text containing `Authorization`, `Bearer`, token, secret URL, and API key values.
- Empty records return zero counts plus a warning and make no provider/link calls.
- Missing email/phone warning now applies only to contact sync plans, not entity/company records.
- Operator approval preflight text now refers to HubSpot live writes/record sync instead of customization apply only.
- API no-secret regression checks serialized response body text.
- Associations are deferred.

## Verification

See `test-output.txt` for exact output.

- `python -m pytest tests/services/test_hubspot_mirror_service.py tests/api/test_hubspot_mirror.py tests/providers/test_hubspot.py tests/db/test_provider_links_repository.py -q` → `52 passed in 2.58s`
- `python -m pytest -q` → `684 passed in 20.47s`
- `git diff --check` → passed with no output

## Files

- Diff summary: `docs/qc/2026-05-14/hubspot-crm-sync/diff-summary.md`
- Test output: `docs/qc/2026-05-14/hubspot-crm-sync/test-output.txt`

## Artifact tracking note

- This QC folder is currently untracked in the dirty workspace; `git diff -- docs/qc/2026-05-14/hubspot-crm-sync` will not show it until staged.
- The workspace also contains unrelated pre-existing tracked modifications/untracked artifacts outside this Phase 4 slice.
