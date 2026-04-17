from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LEAD_MACHINE_MIGRATION = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "202604160001_lead_machine_runtime.sql"
)


def _sql() -> str:
    return LEAD_MACHINE_MIGRATION.read_text(encoding="utf-8").lower()


def test_lead_machine_migration_defines_composite_uniques_before_cross_table_fks() -> None:
    sql = _sql()

    probate_unique = sql.index("constraint probate_leads_tenant_id_unique")
    leads_table = sql.index("create table if not exists public.leads")
    leads_unique = sql.index("constraint leads_tenant_id_unique")
    campaigns_table = sql.index("create table if not exists public.campaigns")
    campaigns_unique = sql.index("constraint campaigns_tenant_id_unique")
    automation_runs_table = sql.index("create table if not exists public.automation_runs")
    automation_runs_unique = sql.index("constraint automation_runs_tenant_id_unique")
    provider_webhooks_table = sql.index("create table if not exists public.provider_webhooks")
    provider_webhooks_unique = sql.index("constraint provider_webhooks_tenant_id_unique")
    lead_events_table = sql.index("create table if not exists public.lead_events")
    lead_events_unique = sql.index("constraint lead_events_tenant_id_unique")

    assert probate_unique < leads_table
    assert leads_unique < campaigns_table
    assert campaigns_unique < automation_runs_table
    assert automation_runs_unique < provider_webhooks_table
    assert provider_webhooks_unique < lead_events_table
    assert lead_events_unique > lead_events_table

