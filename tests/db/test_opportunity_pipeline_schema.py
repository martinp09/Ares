from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20260429183000_opportunity_pipeline_config.sql"


def _sql() -> str:
    return MIGRATION.read_text().lower()


def test_opportunity_pipeline_config_schema_defines_config_and_history_tables() -> None:
    sql = _sql()

    assert "create table if not exists public.opportunity_pipeline_configs" in sql
    assert "create table if not exists public.opportunity_stage_history" in sql
    assert "unique (business_id, environment, source_lane)" in sql
    assert "references public.opportunities (id, business_id, environment)" in sql
    assert "opportunity_pipeline_configs_tenant_isolation" in sql
    assert "opportunity_stage_history_tenant_isolation" in sql
    assert "opportunity_pipeline_configs_touch_updated_at" in sql
