# Diff Summary

## Final fix scope

- Fixed in-memory provider-link normalization gaps found in final Phase 2 review.
- Fixed in-memory provider sync cursor/run provider normalization and sync-run filter behavior.
- Added focused regression tests for initial mixed-case creates and lowercase lookup/list behavior.
- Updated QC evidence with latest focused and full-suite results.
- No live provider calls and no provider writes were performed.
- No broad refactors were made.

## Repository

- `app/db/provider_links.py`
  - `upsert_link` now normalizes `provider`, `provider_object_type`, and `ares_object_type` before in-memory identity-key lookup, create, update, and conflict comparison.
  - In-memory link creates/updates now store and return lowercase identity fields, matching Supabase behavior.
  - `provider_object_id` and `ares_object_id` remain exact-value fields and are not case-normalized.
  - `upsert_cursor` now normalizes `provider` before in-memory identity-key lookup, create, and update.
  - `start_sync_run` now normalizes `provider` before in-memory identity-key lookup and create.
  - `list_sync_runs(provider=...)` now casefolds provider filters for in-memory runs.

## Tests

- `tests/db/test_provider_links_repository.py`
  - Extended mixed-case link identity coverage to assert the initial create returns lowercase `provider`, `provider_object_type`, and `ares_object_type` while preserving exact object IDs.
  - Added coverage that lowercase provider-object lookup finds a link initially created with mixed-case identity fields.
  - Added cursor coverage proving initial create with `provider="HubSpot"` returns/stores `provider="hubspot"` and lowercase `get_cursor` works.
  - Added sync-run coverage proving initial create with `provider="HubSpot"` returns/stores `provider="hubspot"` and `list_sync_runs(provider="hubspot")` finds it.

## QC evidence

- `docs/qc/2026-05-14/provider-object-links/test-output.txt`
  - Updated focused suite result: `21 passed in 0.30s`.
  - Added full backend suite result: `660 passed in 20.01s`.
  - Recorded `git diff --check` passed with no output.
  - Added tracked/untracked artifact note.

- `docs/qc/2026-05-14/provider-object-links/REPORT.md`
  - Updated final safety/result summary and file list.
  - Added current focused/full-suite verification results.
  - Added tracked/untracked artifact note.

## Current verification

- `python -m pytest tests/db/test_provider_links_repository.py tests/db/test_provider_links_schema.py tests/db/test_provider_links_supabase_adapter.py -q` → `21 passed in 0.30s`
- `python -m pytest -q` → `660 passed in 20.01s`
- `git diff --check` → passed with no output
