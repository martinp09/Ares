# Probate Source Identity Supabase Migration QC

Date: 2026-05-16
Repo: `martinp09/Ares`
Branch during live apply: `fix/probate-source-identity-supabase-schema`
Migration: `supabase/migrations/20260516131500_probate_source_identity_dedupe.sql`
Remote target: Supabase project ref suffix `goxw` (full credentials and DB URL intentionally redacted)

## Scope

Apply the durable probate source identity ledger migration to remote Supabase after Martin approved live migration push.

This migration creates `public.probate_source_identities` for durable cross-run probate dedupe with the uniqueness contract:

```text
business_id + environment + source_run_scope + county + source_identity_key
```

It preserves the manual/autonomous separation by keeping `source_run_scope` in the unique key.

## Safety / non-goals

- No Instantly enrollment or sends.
- No email, SMS, Vapi, Slack, HubSpot batch writes, or provider mutations.
- No county/source mutations.
- No raw probate rows, case numbers, party names, or contact data recorded in QC.
- DB URL and credentials were read from the local Ares env and redacted from captured output.

## Live migration notes

First remote apply attempt correctly failed before recording the migration because the migration had `business_id text`, while the live `public.businesses.business_id` is `bigint`.

Fix applied before successful live push:

- changed `probate_source_identities.business_id` from `text` to `bigint`
- removed invalid `business_id = lower(business_id)` lower-case check
- updated schema tests to assert the live-compatible bigint tenant key

The subsequent dry-run still showed only this migration pending, and the subsequent live push succeeded.

## Verification commands

```bash
uv run pytest tests/db/test_probate_source_identity_schema.py tests/services/test_probate_source_file_service.py tests/services/test_nightly_lead_machine_service.py -q
supabase db push --db-url <redacted> --dry-run
supabase db push --db-url <redacted> --yes
supabase migration list --db-url <redacted>
python asyncpg schema verification against information_schema / pg_constraint / pg_policies / pg_indexes
git diff --check
```

## Evidence

- Focused contracts: `36 passed`
- Remote migration list shows `20260516131500` present in both Local and Remote columns.
- Remote schema verification:
  - `schema_verify=ok`
  - `business_id_type=bigint`
  - `column_count=21`
  - RLS enabled: `relrowsecurity=True`
  - policies present: select, insert, update tenant isolation policies
  - indexes present: unique scope key, lookup index, first-seen index, primary key
- `git diff --check`: passed

## Files

- `test-output.txt` — focused contract test output
- `remote-migration-verify-output.txt` — sanitized remote migration list and schema verification
- `diff-summary.md` — exact migration/test patch required by live schema compatibility
- `git-diff-check-output.txt` — whitespace check output

## Result

Status: passed. The durable probate source identity ledger exists in remote Supabase and is migration-history aligned.
