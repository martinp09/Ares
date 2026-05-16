from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260516131500_probate_source_identity_dedupe.sql"
)


def _sql() -> str:
    return MIGRATION.read_text().lower()


def test_probate_source_identity_migration_adds_durable_dedupe_table() -> None:
    sql = _sql()

    assert "create table if not exists public.probate_source_identities" in sql
    assert "business_id bigint not null" in sql
    assert "references public.businesses (business_id, environment)" in sql
    assert "alter table public.probate_source_identities enable row level security" in sql
    assert "public.current_tenant_business_id()" in sql
    assert "public.current_tenant_environment()" in sql


def test_probate_source_identity_migration_keeps_manual_and_autonomous_separate() -> None:
    sql = _sql()

    assert "source_run_scope text not null default 'autonomous'" in sql
    assert "check (source_run_scope in ('autonomous', 'manual'))" in sql
    assert "unique (business_id, environment, source_run_scope, county, source_identity_key)" in sql
    assert "probate_source_identities_lookup_idx" in sql


def test_probate_source_identity_migration_enforces_stable_hashed_case_identity() -> None:
    sql = _sql()

    assert "source_identity_version text not null default 'county_case_sha256_v1'" in sql
    assert "source_identity_key ~ '^probate_case_sha256:[0-9a-f]{64}$'" in sql
    assert "check (source_identity_version = 'county_case_sha256_v1')" in sql
    assert "county in ('harris', 'montgomery')" in sql
    assert "source_identity_key = lower(source_identity_key)" in sql
    assert "business_id = lower(business_id)" not in sql
    assert "seen_count >= 1 and latest_record_count >= 0" in sql
