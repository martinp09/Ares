from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORRECTIVE_MIGRATION = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "202604230002_origin_main_supabase_persistence_wiring_constraints.sql"
)


def _sql() -> str:
    return CORRECTIVE_MIGRATION.read_text(encoding="utf-8").lower()


def test_corrective_migration_backfills_and_tightens_runtime_constraints() -> None:
    sql = _sql()

    assert "update public.organizations_runtime" in sql
    assert "update public.memberships_runtime" in sql
    assert "update public.catalog_entries_runtime" in sql
    assert "update public.agent_installs_runtime" in sql
    assert "raise exception 'organizations_runtime contains duplicate normalized slugs'" in sql
    assert "raise exception 'memberships_runtime contains duplicate org_id/actor_id pairs'" in sql
    assert "raise exception 'catalog_entries_runtime contains duplicate normalized slugs per org'" in sql
    assert "alter table public.memberships_runtime" in sql
    assert "alter column actor_id set not null" in sql
    assert "alter column actor_type set not null" in sql
    assert "alter table public.catalog_entries_runtime" in sql
    assert "alter column slug set not null" in sql
    assert "alter table public.agent_installs_runtime" in sql
    assert "alter column catalog_entry_id set not null" in sql
    assert "alter column installed_agent_id set not null" in sql


def test_corrective_migration_aligns_slug_uniqueness_with_runtime_normalization() -> None:
    sql = _sql()

    assert "drop index if exists organizations_runtime_slug_idx" in sql
    assert "lower(btrim(slug))" in sql
    assert "create unique index if not exists catalog_entries_runtime_org_slug_norm_idx" in sql
    assert "on public.catalog_entries_runtime (org_id, lower(btrim(slug)))" in sql
