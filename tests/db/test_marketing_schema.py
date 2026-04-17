from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETING_MIGRATION = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "202604140001_lease_option_marketing_mvp.sql"
)


def _sql() -> str:
    return MARKETING_MIGRATION.read_text(encoding="utf-8").lower()


def test_marketing_migration_adds_required_tables() -> None:
    sql = _sql()

    assert "create table if not exists public.messages" in sql
    assert "create table if not exists public.booking_events" in sql
    assert "create table if not exists public.sequence_enrollments" in sql


def test_marketing_migration_adds_sequence_status_guardrail() -> None:
    sql = _sql()

    assert re.search(
        r"constraint\s+sequence_enrollments_status_check\s+check\s*\(\s*status\s+in\s*\('active',\s*'paused',\s*'completed',\s*'stopped'\)\s*\)",
        sql,
    )


def test_marketing_migration_matches_live_booking_event_types() -> None:
    sql = _sql()

    assert re.search(
        r"constraint\s+booking_events_event_type_check\s+check\s*\(\s*event_type\s+in\s*\('booked',\s*'rescheduled',\s*'cancelled'\)\s*\)",
        sql,
    )


def test_marketing_migration_adds_minimum_indexes_for_marketing_queries() -> None:
    sql = _sql()

    assert (
        "create index if not exists messages_contact_id_created_at_idx" in sql
        or "create index if not exists messages_conversation_id_created_at_idx" in sql
    )
    assert "create index if not exists booking_events_contact_id_occurred_at_idx" in sql
    assert "create unique index if not exists sequence_enrollments_active_unique_idx" in sql
