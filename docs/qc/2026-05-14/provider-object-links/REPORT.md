# Provider Object Links / Sync Runs Phase 2 QC

## Scope

Final review-fix completion for Phase 2 provider mirror state normalization and QC evidence only:

- Aligned in-memory `ProviderLinksRepository.upsert_link` create/update paths with Supabase normalization for identity fields: `provider`, `provider_object_type`, and `ares_object_type` are stored/returned lowercase.
- Preserved exact `provider_object_id` and `ares_object_id` values in in-memory link storage.
- Aligned in-memory `ProviderSyncCursor` create/update storage with Supabase normalization for `provider`.
- Aligned in-memory `ProviderSyncRun` create storage with Supabase normalization for `provider`.
- Made in-memory `list_sync_runs(provider=...)` filtering case-insensitive.
- Added focused tests for mixed-case initial create behavior and lowercase lookup/list behavior.

No live provider calls were made. No provider writes were added. Dry-run HubSpot preview behavior remains payload-only.

## Safety result

- Ares object IDs remain canonical; provider IDs are mirrored in a separate link index.
- Provider/object identity values normalize to lowercase where they are identity fields.
- Provider object IDs and Ares object IDs preserve original casing/values.
- In-memory behavior now matches Supabase adapter/database normalization contracts for provider link, cursor, and sync-run identity fields.
- Supabase schema enforces lower-case identity/provider fields at the database boundary.
- Duplicate Supabase insert races continue to be recovered by refetching the existing row, patching with the requested payload, and mapping back to `ProviderObjectLink`.

## Verification

- `python -m pytest tests/db/test_provider_links_repository.py tests/db/test_provider_links_schema.py tests/db/test_provider_links_supabase_adapter.py -q` → `21 passed in 0.30s`
- `python -m pytest -q` → `660 passed in 20.01s`
- `git diff --check` → passed with no output

## Artifact tracking note

- `git status --short` reports this QC folder under untracked `docs/qc/2026-05-14/` along with other existing untracked Phase 2 artifacts/files.
- The working tree also contains unrelated tracked modifications predating/adjacent to this lane (for example `.env.example`, `CONTEXT.md`, `app/api/mission_control.py`, `app/core/config.py`, `app/db/client.py`, `app/models/mission_control.py`, `docs/integrations/tracerfy-skiptrace.md`, `memory.md`, and `tests/conftest.py`).
- No files were staged or committed.

## Files changed in this final fix pass

- `app/db/provider_links.py`
- `tests/db/test_provider_links_repository.py`
- `docs/qc/2026-05-14/provider-object-links/REPORT.md`
- `docs/qc/2026-05-14/provider-object-links/diff-summary.md`
- `docs/qc/2026-05-14/provider-object-links/test-output.txt`
