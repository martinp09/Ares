from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[2] / "supabase" / "migrations" / "20260516090000_sms_reply_agent_runtime.sql"


def _sql() -> str:
    return MIGRATION.read_text().lower()


def test_sms_agent_migration_adds_runtime_tables_and_tenant_rls() -> None:
    sql = _sql()

    for table in [
        "sms_agent_jobs",
        "sms_agent_decisions",
        "sms_agent_eval_labels",
        "sms_agent_archives",
    ]:
        assert f"create table if not exists public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
        assert f"create policy {table}_tenant_isolation" in sql
    assert sql.count("references public.businesses (business_id, environment)") >= 4
    assert "public.current_tenant_business_id()" in sql
    assert "public.current_tenant_environment()" in sql


def test_sms_agent_migration_defines_core_constraints_indexes_and_trigger() -> None:
    sql = _sql()

    assert "constraint sms_agent_jobs_status_check" in sql
    assert "check (status in ('pending', 'processing', 'completed', 'blocked', 'failed_retryable', 'failed_terminal'))" in sql
    assert "constraint sms_agent_decisions_confidence_check check (confidence >= 0 and confidence <= 1)" in sql
    assert "constraint sms_agent_jobs_decision_fkey" in sql
    assert "references public.sms_agent_decisions(id, business_id, environment)" in sql
    assert "create unique index if not exists sms_agent_jobs_webhook_message_unique_idx" in sql
    assert "where provider_webhook_id is not null or message_id is not null or payload_hash is not null" in sql
    assert "create index if not exists sms_agent_jobs_pending_idx" in sql
    assert "create index if not exists sms_agent_decisions_job_idx" in sql
    assert "create index if not exists sms_agent_eval_labels_decision_idx" in sql
    assert "drop trigger if exists sms_agent_jobs_touch_updated_at" in sql
    assert "create trigger sms_agent_jobs_touch_updated_at" in sql


def test_sms_agent_migration_defines_scoped_job_decision_constraints() -> None:
    sql = _sql()

    assert "constraint sms_agent_jobs_id_tenant_unique unique (id, business_id, environment)" in sql
    assert "constraint sms_agent_decisions_id_tenant_unique unique (id, business_id, environment)" in sql
    assert "constraint sms_agent_decisions_job_fkey" in sql
    assert "foreign key (job_id, business_id, environment)" in sql
    assert "references public.sms_agent_jobs(id, business_id, environment)" in sql
    assert "foreign key (decision_id, business_id, environment)" in sql
    assert "references public.sms_agent_decisions(id, business_id, environment)" in sql
    assert "on delete set null" in sql
