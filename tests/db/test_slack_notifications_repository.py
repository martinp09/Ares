from io import BytesIO
from pathlib import Path
from threading import Barrier, Thread
from time import sleep
from urllib.error import HTTPError

import pytest
from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.slack_notifications import SlackNotificationsRepository
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260516012000_slack_notifications.sql"
)
CHIEF_OF_STAFF_ROUTE_MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260518130327_chief_of_staff_slack_route.sql"
)


def build_repository() -> SlackNotificationsRepository:
    return SlackNotificationsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))


def test_record_attempt_dedupes_by_scope_route_and_key() -> None:
    repository = build_repository()
    attempt = SlackNotificationAttempt(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.HOT_LEADS,
        dedupe_key="hot-lead:lead_123",
        channel_id="CHOT",
        status="sent",
        slack_message_ts="1715788800.000100",
        payload={"lead_id": "lead_123"},
    )

    first = repository.record_attempt(attempt)
    second = repository.record_attempt(attempt.model_copy(update={"slack_message_ts": "1715788800.000200"}))

    assert first.id == second.id
    assert isinstance(first.created_at, str)
    assert second.deduped is True
    assert second.slack_message_ts == "1715788800.000100"
    assert (
        repository.get_by_dedupe_key(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
        )
        == first
    )


def test_record_attempt_persists_failed_attempt_details() -> None:
    repository = build_repository()
    attempt = SlackNotificationAttempt(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.INSTANTLY_REPLIES,
        dedupe_key="reply:abc",
        channel_id="CREPLY",
        status="failed",
        payload={"provider": "instantly"},
        error_message="channel_not_found",
    )

    recorded = repository.record_attempt(attempt)
    fetched = repository.get(recorded.id)

    assert fetched is not None
    assert fetched == recorded
    assert fetched.status == "failed"
    assert fetched.error_message == "channel_not_found"
    assert fetched.sent_at is None


def test_record_attempt_persists_skipped_attempt_and_dedupes_replays() -> None:
    repository = build_repository()
    attempt = SlackNotificationAttempt(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.LEASE_OPTION_INBOUND,
        dedupe_key="lease-option:intake_123",
        channel_id=None,
        status="skipped",
        payload={"lead_id": "lead_456", "reason": "missing_channel"},
        error_message="slack_channel_not_configured",
    )

    first = repository.record_attempt(attempt)
    second = repository.record_attempt(
        attempt.model_copy(
            update={
                "channel_id": "CLEASE",
                "payload": {"lead_id": "lead_456", "reason": "replay"},
                "error_message": "replayed",
            }
        )
    )
    listed = repository.list(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.LEASE_OPTION_INBOUND,
    )

    assert first.status == "skipped"
    assert first.channel_id is None
    assert first.payload == {"lead_id": "lead_456", "reason": "missing_channel"}
    assert first.error_message == "slack_channel_not_configured"
    assert second.id == first.id
    assert second.deduped is True
    assert second.status == "skipped"
    assert second.channel_id is None
    assert second.payload == first.payload
    assert listed == [first]


def test_update_attempt_persists_final_state_in_memory() -> None:
    repository = build_repository()
    attempt = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="skipped",
            payload={"lead_id": "lead_123"},
        )
    )

    updated = repository.update_attempt(
        attempt.model_copy(
            update={
                "status": "sent",
                "slack_message_ts": "1715788800.000100",
                "sent_at": "2026-05-15T09:30:01Z",
            }
        )
    )
    fetched = repository.get(attempt.id)

    assert updated.status == "sent"
    assert updated.slack_message_ts == "1715788800.000100"
    assert updated.sent_at == "2026-05-15T09:30:01Z"
    assert fetched == updated


def test_reserve_attempt_for_delivery_claims_stale_pending_once_in_memory() -> None:
    repository = build_repository()
    existing = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="failed",
            payload={"lead_id": "lead_123"},
            error_message="slack_delivery_pending",
            created_at="2026-05-16T11:45:00+00:00",
        )
    )

    first_claim = repository.reserve_attempt_for_delivery(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.HOT_LEADS,
        dedupe_key="hot-lead:lead_123",
        channel_id="CHOT",
        payload={"lead_id": "lead_123", "attempt": 1},
        now="2026-05-16T12:00:00+00:00",
        pending_retry_after_seconds=300,
        retryable_error_message="slack_delivery_pending",
    )
    second_claim = repository.reserve_attempt_for_delivery(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.HOT_LEADS,
        dedupe_key="hot-lead:lead_123",
        channel_id="CHOT",
        payload={"lead_id": "lead_123", "attempt": 2},
        now="2026-05-16T12:00:01+00:00",
        pending_retry_after_seconds=300,
        retryable_error_message="slack_delivery_pending",
    )
    persisted = repository.get(existing.id)

    assert first_claim.id == existing.id
    assert first_claim.deduped is False
    assert first_claim.status == "failed"
    assert first_claim.error_message == "slack_delivery_pending"
    assert first_claim.created_at == "2026-05-16T12:00:00+00:00"
    assert first_claim.payload == {"lead_id": "lead_123", "attempt": 1}
    assert second_claim.id == existing.id
    assert second_claim.deduped is True
    assert second_claim.created_at == "2026-05-16T12:00:00+00:00"
    assert second_claim.payload == {"lead_id": "lead_123", "attempt": 1}
    assert persisted == first_claim


def test_concurrent_reserve_attempt_for_delivery_claims_stale_pending_once_in_memory(monkeypatch) -> None:
    repository = build_repository()
    repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="failed",
            error_message="slack_delivery_pending",
            created_at="2026-05-16T11:45:00+00:00",
        )
    )
    original_stale_check = SlackNotificationsRepository._is_stale_retryable_attempt
    start = Barrier(2)
    claims: list[SlackNotificationAttempt] = []
    errors: list[BaseException] = []

    def slow_stale_check(*args, **kwargs) -> bool:
        sleep(0.05)
        return original_stale_check(*args, **kwargs)

    monkeypatch.setattr(SlackNotificationsRepository, "_is_stale_retryable_attempt", staticmethod(slow_stale_check))

    def claim() -> None:
        try:
            start.wait(timeout=2)
            claims.append(
                repository.reserve_attempt_for_delivery(
                    business_id="limitless",
                    environment="prod",
                    route=SlackNotificationRoute.HOT_LEADS,
                    dedupe_key="hot-lead:lead_123",
                    channel_id="CHOT",
                    payload={},
                    now="2026-05-16T12:00:00+00:00",
                    pending_retry_after_seconds=300,
                    retryable_error_message="slack_delivery_pending",
                )
            )
        except BaseException as exc:
            errors.append(exc)

    threads = [Thread(target=claim), Thread(target=claim)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert errors == []
    assert len(claims) == 2
    assert sum(claim.deduped is False for claim in claims) == 1
    assert sum(claim.deduped is True for claim in claims) == 1


def test_supabase_adapter_fetches_existing_attempt_before_insert(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    inserted: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        assert table == "slack_notifications"
        assert params["business_id"] == "eq.7"
        assert params["route"] == "eq.hot_leads"
        assert params["dedupe_key"] == "eq.hot-lead:lead_123"
        return [
            {
                "id": "slack_notice_existing",
                "business_id": 7,
                "environment": "prod",
                "route": "hot_leads",
                "dedupe_key": "hot-lead:lead_123",
                "channel_id": "CHOT",
                "status": "sent",
                "slack_message_ts": "1715788800.000100",
                "payload": {"lead_id": "lead_123"},
                "error_message": None,
                "created_at": "2026-05-15T09:30:00Z",
                "sent_at": "2026-05-15T09:30:01Z",
            }
        ]

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        inserted.append(rows[0])
        raise AssertionError("duplicate attempts should not insert a new Slack notification row")

    monkeypatch.setattr("app.db.slack_notifications.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.slack_notifications.insert_rows", fake_insert_rows)
    monkeypatch.setattr(
        "app.db.slack_notifications.resolve_tenant",
        lambda business_id, environment, settings=None: type(
            "Tenant",
            (),
            {"business_pk": 7, "environment": environment},
        )(),
    )

    repository = SlackNotificationsRepository(settings=settings)
    recorded = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="sent",
            payload={"lead_id": "lead_123"},
        )
    )

    assert inserted == []
    assert recorded.id == "slack_notice_existing"
    assert recorded.business_id == "7"
    assert recorded.deduped is True
    assert recorded.created_at == "2026-05-15T09:30:00Z"
    assert isinstance(recorded.created_at, str)
    assert recorded.sent_at == "2026-05-15T09:30:01Z"
    assert isinstance(recorded.sent_at, str)


def _duplicate_http_error(status: int) -> HTTPError:
    body = b'{"code":"23505","message":"duplicate key value violates unique constraint"}'
    return HTTPError("https://example.supabase.co/rest/v1/slack_notifications", status, "duplicate", {}, BytesIO(body))


@pytest.mark.parametrize("status", [409, 400])
def test_supabase_duplicate_insert_race_refetches_existing_attempt(monkeypatch, status: int) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    existing_row = {
        "id": "slack_notice_existing",
        "business_id": 7,
        "environment": "prod",
        "route": "hot_leads",
        "dedupe_key": "hot-lead:lead_123",
        "channel_id": "CHOT",
        "status": "sent",
        "slack_message_ts": "1715788800.000100",
        "payload": {"lead_id": "lead_123"},
        "error_message": None,
        "created_at": "2026-05-15T09:30:00Z",
        "sent_at": "2026-05-15T09:30:01Z",
    }
    calls = {"fetch": 0, "insert": 0}

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        assert table == "slack_notifications"
        calls["fetch"] += 1
        if calls["fetch"] == 1:
            return []
        assert params["business_id"] == "eq.7"
        assert params["environment"] == "eq.prod"
        assert params["route"] == "eq.hot_leads"
        assert params["dedupe_key"] == "eq.hot-lead:lead_123"
        return [dict(existing_row)]

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        assert table == "slack_notifications"
        calls["insert"] += 1
        raise _duplicate_http_error(status)

    monkeypatch.setattr("app.db.slack_notifications.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.slack_notifications.insert_rows", fake_insert_rows)
    monkeypatch.setattr(
        "app.db.slack_notifications.resolve_tenant",
        lambda business_id, environment, settings=None: type(
            "Tenant",
            (),
            {"business_pk": 7, "environment": environment},
        )(),
    )

    repository = SlackNotificationsRepository(settings=settings)
    recorded = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="sent",
            payload={"lead_id": "lead_123"},
        )
    )

    assert calls == {"fetch": 2, "insert": 1}
    assert recorded.id == "slack_notice_existing"
    assert recorded.deduped is True


def test_supabase_update_attempt_patches_final_state_with_tenant_scope(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    captured: dict[str, object] = {}

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        assert table == "slack_notifications"
        captured["params"] = params
        captured["row"] = row
        return [
            {
                "id": "slack_notice_existing",
                "business_id": 7,
                "environment": "prod",
                "route": "hot_leads",
                "dedupe_key": "hot-lead:lead_123",
                "channel_id": "CHOT",
                "status": "sent",
                "slack_message_ts": "1715788800.000100",
                "payload": {"lead_id": "lead_123"},
                "error_message": None,
                "created_at": "2026-05-15T09:30:00Z",
                "sent_at": "2026-05-15T09:30:01Z",
            }
        ]

    monkeypatch.setattr("app.db.slack_notifications.patch_rows", fake_patch_rows)
    monkeypatch.setattr(
        "app.db.slack_notifications.resolve_tenant",
        lambda business_id, environment, settings=None: type(
            "Tenant",
            (),
            {"business_pk": 7, "environment": environment},
        )(),
    )

    repository = SlackNotificationsRepository(settings=settings)
    updated = repository.update_attempt(
        SlackNotificationAttempt(
            id="slack_notice_existing",
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="sent",
            slack_message_ts="1715788800.000100",
            payload={"lead_id": "lead_123"},
            error_message=None,
            created_at="2026-05-15T09:30:00Z",
            sent_at="2026-05-15T09:30:01Z",
        )
    )

    assert captured["params"] == {
        "id": "eq.slack_notice_existing",
        "business_id": "eq.7",
        "environment": "eq.prod",
    }
    assert captured["row"] == {
        "channel_id": "CHOT",
        "status": "sent",
        "slack_message_ts": "1715788800.000100",
        "payload": {"lead_id": "lead_123"},
        "error_message": None,
        "sent_at": "2026-05-15T09:30:01Z",
    }
    assert updated.business_id == "7"
    assert updated.status == "sent"


def test_supabase_reserve_attempt_conservatively_dedupes_existing_pending_without_claim(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        assert table == "slack_notifications"
        assert params["business_id"] == "eq.7"
        assert params["route"] == "eq.hot_leads"
        assert params["dedupe_key"] == "eq.hot-lead:lead_123"
        return [
            {
                "id": "slack_notice_existing",
                "business_id": 7,
                "environment": "prod",
                "route": "hot_leads",
                "dedupe_key": "hot-lead:lead_123",
                "channel_id": "CHOT",
                "status": "failed",
                "slack_message_ts": None,
                "payload": {"lead_id": "lead_123"},
                "error_message": "slack_delivery_pending",
                "created_at": "2026-05-16T11:45:00Z",
                "sent_at": None,
            }
        ]

    monkeypatch.setattr("app.db.slack_notifications.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr(
        "app.db.slack_notifications.insert_rows",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("existing pending must not insert")),
    )
    monkeypatch.setattr(
        "app.db.slack_notifications.patch_rows",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("existing pending must not be claimed")),
    )
    monkeypatch.setattr(
        "app.db.slack_notifications.resolve_tenant",
        lambda business_id, environment, settings=None: type(
            "Tenant",
            (),
            {"business_pk": 7, "environment": environment},
        )(),
    )

    repository = SlackNotificationsRepository(settings=settings)
    reserved = repository.reserve_attempt_for_delivery(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.HOT_LEADS,
        dedupe_key="hot-lead:lead_123",
        channel_id="CHOT",
        payload={"lead_id": "lead_123"},
        now="2026-05-16T12:00:00+00:00",
        pending_retry_after_seconds=300,
        retryable_error_message="slack_delivery_pending",
    )

    assert reserved.id == "slack_notice_existing"
    assert reserved.status == "failed"
    assert reserved.error_message == "slack_delivery_pending"
    assert reserved.deduped is True


def test_supabase_get_requires_tenant_scope() -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    repository = SlackNotificationsRepository(settings=settings)

    with pytest.raises(ValueError, match="business_id and environment are required"):
        repository.get("slack_notice_existing")


def test_supabase_get_fetches_attempt_with_tenant_scope(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    captured: dict[str, dict[str, str]] = {}

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        assert table == "slack_notifications"
        captured["params"] = params
        return [
            {
                "id": "slack_notice_existing",
                "business_id": 7,
                "environment": "prod",
                "route": "errors",
                "dedupe_key": "error:run_1",
                "channel_id": "CERR",
                "status": "failed",
                "slack_message_ts": None,
                "payload": {"run_id": "run_1"},
                "error_message": "provider_error",
                "created_at": "2026-05-15T09:30:00Z",
                "sent_at": None,
            }
        ]

    monkeypatch.setattr("app.db.slack_notifications.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr(
        "app.db.slack_notifications.resolve_tenant",
        lambda business_id, environment, settings=None: type(
            "Tenant",
            (),
            {"business_pk": 7, "environment": environment},
        )(),
    )

    repository = SlackNotificationsRepository(settings=settings)
    attempt = repository.get("slack_notice_existing", business_id="limitless", environment="prod")

    assert captured["params"] == {
        "select": "*",
        "id": "eq.slack_notice_existing",
        "business_id": "eq.7",
        "environment": "eq.prod",
        "limit": "1",
    }
    assert attempt is not None
    assert attempt.business_id == "7"
    assert attempt.environment == "prod"
    assert attempt.route == SlackNotificationRoute.ERRORS


@pytest.mark.parametrize(
    ("business_id", "environment"),
    [
        ("limitless", None),
        ("7", None),
        (None, "prod"),
    ],
)
def test_supabase_list_requires_business_and_environment_scope(business_id: str | None, environment: str | None) -> None:
    settings = Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    repository = SlackNotificationsRepository(settings=settings)

    with pytest.raises(ValueError, match="business_id and environment are required"):
        repository.list(business_id=business_id, environment=environment)


def test_slack_notifications_migration_adds_durable_attempt_table() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.slack_notifications" in sql
    assert "constraint slack_notifications_scope_route_dedupe_unique" in sql
    assert "unique (business_id, environment, route, dedupe_key)" in sql
    assert "create index if not exists slack_notifications_scope_route_created_idx" in sql
    assert "alter table public.slack_notifications enable row level security" in sql
    assert "create policy slack_notifications_tenant_isolation" in sql


def test_chief_of_staff_route_migration_extends_route_check() -> None:
    sql = CHIEF_OF_STAFF_ROUTE_MIGRATION.read_text(encoding="utf-8").lower()

    assert "drop constraint if exists slack_notifications_route_check" in sql
    assert "add constraint slack_notifications_route_check" in sql
    assert "'chief_of_staff_digest'" in sql
