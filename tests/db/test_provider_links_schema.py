from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20260514090000_provider_object_links.sql"


def _sql() -> str:
    return MIGRATION.read_text().lower()


def test_provider_links_migration_adds_all_phase_2_tables() -> None:
    sql = _sql()

    assert "create table if not exists public.provider_object_links" in sql
    assert "create table if not exists public.provider_sync_cursors" in sql
    assert "create table if not exists public.provider_sync_runs" in sql
    assert sql.count("references public.businesses (business_id, environment)") >= 3
    assert "alter table public.provider_object_links enable row level security" in sql
    assert "alter table public.provider_sync_cursors enable row level security" in sql
    assert "alter table public.provider_sync_runs enable row level security" in sql
    assert "public.current_tenant_business_id()" in sql
    assert "public.current_tenant_environment()" in sql


def test_provider_object_links_migration_defines_identity_constraints_and_indexes() -> None:
    sql = _sql()

    assert "check (link_status in ('active', 'stale', 'conflict', 'archived'))" in sql
    assert "unique (business_id, environment, provider, provider_object_type, provider_object_id)" in sql
    assert "unique (business_id, environment, provider, ares_object_type, ares_object_id, provider_object_type)" in sql
    assert "create index if not exists provider_object_links_ares_lookup_idx" in sql
    assert "create index if not exists provider_object_links_provider_lookup_idx" in sql
    assert "drop trigger if exists provider_object_links_touch_updated_at" in sql


def test_provider_sync_cursor_and_run_migration_defines_guards() -> None:
    sql = _sql()

    assert "unique (business_id, environment, provider, sync_name)" in sql
    assert "unique (business_id, environment, provider, sync_name, idempotency_key)" in sql
    assert "check (direction in ('ares_to_provider', 'provider_to_ares', 'bidirectional', 'dry_run'))" in sql
    assert "check (status in ('queued', 'in_progress', 'completed', 'failed', 'cancelled'))" in sql
    assert "scanned_count >= 0" in sql
    assert "drop trigger if exists provider_sync_cursors_touch_updated_at" in sql
    assert "drop trigger if exists provider_sync_runs_touch_updated_at" in sql


def test_provider_links_migration_enforces_lowercase_identity_columns() -> None:
    sql = _sql()

    assert "constraint provider_object_links_identity_lower_check" in sql
    assert "provider = lower(provider)" in sql
    assert "provider_object_type = lower(provider_object_type)" in sql
    assert "ares_object_type = lower(ares_object_type)" in sql
    assert "constraint provider_sync_cursors_provider_lower_check" in sql
    assert "constraint provider_sync_runs_provider_lower_check" in sql
