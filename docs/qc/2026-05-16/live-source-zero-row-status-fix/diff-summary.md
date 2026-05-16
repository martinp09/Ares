# Diff summary — live source zero-row status fix

## Files changed

- `app/services/probate_autopilot_manifest_service.py`
  - Treats a declared live-source/local-export adapter result as a real source result even when the county returned zero rows.
  - Prevents successful zero-row live county fetches from falling back to the old Phase 1 placeholder manifest.
  - Sets source-run `live_source_adapter_status` to `live_source_adapter` for live county adapters and `local_export_file` for local export results.

- `tests/services/test_probate_source_provider_service.py`
  - Adds a fake zero-row live source adapter.
  - Adds regression coverage proving zero-row live adapter runs create real source-run artifacts and do not emit the misleading `live county scraping is deferred` warning.
  - Tightens existing live adapter test to assert `live_source_adapter_status=live_source_adapter`.

## Side-effect boundary

- This patch does not enable outbound SMS/email/Instantly/Vapi/HubSpot writes.
- The live-source/intelligence gates were already enabled in Trigger prod env and VPS env; the bug was stale zero-row status/warning behavior, not missing env gates.
