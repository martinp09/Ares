from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20260429184500_crm_record_saved_views.sql"


def _sql() -> str:
    return MIGRATION.read_text().lower()


def test_crm_record_saved_views_schema_is_tenant_scoped_and_filter_backed() -> None:
    sql = _sql()

    assert "create table if not exists public.crm_record_saved_views" in sql
    assert "filters jsonb not null default '{}'::jsonb" in sql
    assert "unique (business_id, environment, slug)" in sql
    assert "references public.businesses (business_id, environment)" in sql
    assert "crm_record_saved_views_tenant_isolation" in sql
    assert "crm_record_saved_views_touch_updated_at" in sql
