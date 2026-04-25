from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def _all_migrations_sql() -> str:
    return "\n".join(path.read_text() for path in sorted(MIGRATIONS_DIR.glob("*.sql"))).lower()


def test_title_packets_schema_is_supabase_wired_for_lead_machine() -> None:
    sql = _all_migrations_sql()

    assert "create table if not exists public.title_packets" in sql
    assert "references public.businesses (business_id, environment)" in sql
    assert "references public.leads (id, business_id, environment)" in sql
    assert "unique (business_id, environment, identity_key)" in sql
    assert "alter table public.title_packets enable row level security" in sql
    assert "create policy title_packets_tenant_isolation" in sql
    assert "create index if not exists title_packets_scope_lead_idx" in sql
