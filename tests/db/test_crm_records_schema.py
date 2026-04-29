from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _all_migrations_sql() -> str:
    return "\n".join(path.read_text() for path in sorted(MIGRATIONS_DIR.glob("*.sql"))).lower()


def test_crm_records_schema_is_supabase_wired_for_records_registry() -> None:
    sql = _all_migrations_sql()

    assert "create table if not exists public.crm_records" in sql
    assert "create table if not exists public.crm_source_records" in sql
    assert "create table if not exists public.crm_record_source_memberships" in sql
    assert "create table if not exists public.crm_record_status_history" in sql
    assert "create table if not exists public.crm_record_promotions" in sql
    assert "references public.businesses (business_id, environment)" in sql
    assert "references public.crm_records (id, business_id, environment)" in sql
    assert "references public.opportunities (id, business_id, environment)" in sql
    assert "unique (business_id, environment, identity_key)" in sql
    assert "alter table public.crm_records enable row level security" in sql
    assert "create policy crm_records_tenant_isolation" in sql
    assert "create index if not exists crm_records_scope_status_idx" in sql
