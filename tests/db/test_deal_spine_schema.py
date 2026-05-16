from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20260516011000_deal_spine_runtime.sql"


def test_deal_spine_migration_adds_runtime_tables() -> None:
    sql = MIGRATION.read_text()
    for table in [
        "deal_records_runtime",
        "deal_parties_runtime",
        "deal_tasks_runtime",
        "deal_document_requirements_runtime",
        "deal_audit_events_runtime",
        "deal_stage_events_runtime",
        "deal_risk_flags_runtime",
    ]:
        assert f"create table if not exists public.{table}" in sql
        assert f"{table}_" in sql


def test_deal_spine_migration_matches_normalized_runtime_columns() -> None:
    sql = MIGRATION.read_text()
    for column in [
        "business_id text not null",
        "environment text not null",
        "deal_id text not null",
        "payload_json jsonb not null default '{}'::jsonb",
    ]:
        assert column in sql
    for column in [
        "source_lane text",
        "strategy_lane text",
        "stage text",
        "county text",
        "no_send boolean",
        "provider_sends_enabled boolean",
        "task_type text",
        "document_type text",
        "required_stage text",
        "event_type text",
        "to_stage text",
        "severity text",
        "active boolean",
    ]:
        assert column in sql
