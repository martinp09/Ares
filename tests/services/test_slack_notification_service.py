from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.slack_notifications import SlackNotificationsRepository
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute
from app.services.slack_notification_service import SlackNotificationService


def build_repository() -> SlackNotificationsRepository:
    return SlackNotificationsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))


def build_service(
    *,
    settings: Settings,
    repository: SlackNotificationsRepository,
    sent: list[dict[str, Any]],
    response: dict[str, Any] | Exception | None = None,
    clock: Any | None = None,
) -> SlackNotificationService:
    def sender(outbound_request: dict[str, Any]) -> dict[str, Any] | None:
        sent.append(outbound_request)
        if isinstance(response, Exception):
            raise response
        if response is not None:
            return response
        return {"ok": True, "channel": outbound_request["payload"]["channel"], "ts": "1715788800.000100"}

    kwargs: dict[str, Any] = {"settings": settings, "repository": repository, "request_sender": sender}
    if clock is not None:
        kwargs["clock"] = clock
    return SlackNotificationService(**kwargs)


def test_chief_of_staff_route_posts_to_dedicated_channel() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_chief_of_staff="CCOS",
        ),
        repository=repository,
        sent=sent,
    )

    result = service.notify(
        route=SlackNotificationRoute.CHIEF_OF_STAFF_DIGEST,
        business_id="limitless",
        environment="prod",
        dedupe_key="chief-of-staff:2026-05-18",
        text="Chief of Staff brief",
        blocks=[],
        payload={"kind": "ares_chief_of_staff_brief_v0"},
    )

    assert result.status == "sent"
    assert result.channel_id == "CCOS"
    assert sent[0]["payload"]["channel"] == "CCOS"


@pytest.mark.parametrize(
    ("settings", "expected_error"),
    [
        (
            Settings(
                _env_file=None,
                slack_notifications_enabled=False,
                slack_bot_token="xoxb-test",
                slack_channel_hot_leads="CHOT",
            ),
            "slack_notifications_disabled",
        ),
        (
            Settings(
                _env_file=None,
                slack_notifications_enabled=True,
                slack_bot_token=None,
                slack_channel_hot_leads="CHOT",
            ),
            "slack_bot_token_missing",
        ),
        (
            Settings(
                _env_file=None,
                slack_notifications_enabled=True,
                slack_bot_token="xoxb-test",
                slack_channel_hot_leads=None,
            ),
            "slack_channel_not_configured",
        ),
    ],
)
def test_skip_paths_record_durable_attempt_without_posting(settings: Settings, expected_error: str) -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    service = build_service(settings=settings, repository=repository, sent=sent)

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
        payload={"lead_id": "lead_123"},
    )
    persisted = repository.get(result.id)

    assert sent == []
    assert result.status == "skipped"
    assert result.error_message == expected_error
    assert persisted == result
    assert persisted is not None
    assert persisted.payload == {"lead_id": "lead_123"}


def test_configured_route_posts_to_slack_and_persists_sent_status() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
    )
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "*Hot lead*"}}]

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=blocks,
        payload={"lead_id": "lead_123"},
    )
    persisted = repository.get(result.id)

    assert sent == [
        {
            "endpoint": "https://slack.com/api/chat.postMessage",
            "headers": {
                "Authorization": "Bearer xoxb-test",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            "payload": {
                "channel": "CHOT",
                "text": "Hot lead",
                "blocks": blocks,
                "unfurl_links": False,
                "unfurl_media": False,
            },
        }
    ]
    assert result.status == "sent"
    assert result.channel_id == "CHOT"
    assert result.slack_message_ts == "1715788800.000100"
    assert isinstance(result.sent_at, str)
    assert persisted == result


def test_configured_route_reserves_live_attempt_as_retryable_failed_before_posting() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()

    def sender(outbound_request: dict[str, Any]) -> dict[str, Any]:
        sent.append(outbound_request)
        reserved = repository.get_by_dedupe_key(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
        )
        assert reserved is not None
        assert reserved.status == "failed"
        assert reserved.error_message == "slack_delivery_pending"
        return {"ok": True, "channel": outbound_request["payload"]["channel"], "ts": "1715788800.000100"}

    service = SlackNotificationService(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        request_sender=sender,
    )

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )

    assert len(sent) == 1
    assert result.status == "sent"


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        ({"ok": False, "error": "channel_not_found"}, "channel_not_found"),
        (RuntimeError("network unavailable"), "network unavailable"),
    ],
)
def test_slack_failure_records_durable_failed_attempt(response: dict[str, Any] | Exception, expected_error: str) -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_instantly_replies="CREPLIES",
        ),
        repository=repository,
        sent=sent,
        response=response,
    )

    result = service.notify(
        route=SlackNotificationRoute.INSTANTLY_REPLIES,
        business_id="limitless",
        environment="prod",
        dedupe_key="instantly:reply_123",
        text="Instantly reply",
        blocks=[],
    )
    persisted = repository.get(result.id)

    assert len(sent) == 1
    assert result.status == "failed"
    assert result.error_message == expected_error
    assert result.sent_at is None
    assert persisted == result


def test_duplicate_dedupe_key_returns_existing_attempt_without_second_post() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_lease_option_inbound="CLEASE",
        ),
        repository=repository,
        sent=sent,
    )

    first = service.notify(
        route=SlackNotificationRoute.LEASE_OPTION_INBOUND,
        business_id="limitless",
        environment="prod",
        dedupe_key="lease-option:intake_123",
        text="Lease option inbound",
        blocks=[],
    )
    second = service.notify(
        route=SlackNotificationRoute.LEASE_OPTION_INBOUND,
        business_id="limitless",
        environment="prod",
        dedupe_key="lease-option:intake_123",
        text="Lease option inbound replay",
        blocks=[],
    )

    assert len(sent) == 1
    assert first.status == "sent"
    assert second.id == first.id
    assert second.deduped is True
    assert second.slack_message_ts == first.slack_message_ts


def test_existing_intentional_skipped_attempt_dedupes_without_second_post() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    existing = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id=None,
            status="skipped",
            error_message="slack_channel_not_configured",
        )
    )
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
    )

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )

    assert sent == []
    assert result.id == existing.id
    assert result.status == "skipped"
    assert result.deduped is True


def test_existing_retryable_incomplete_reservation_can_post_and_update() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    existing = repository.record_attempt(
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
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
        clock=lambda: now,
    )

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )
    persisted = repository.get(existing.id)

    assert len(sent) == 1
    assert result.id == existing.id
    assert result.status == "sent"
    assert result.error_message is None
    assert persisted == result


def test_existing_fresh_pending_reservation_dedupes_without_posting() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    existing = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="failed",
            error_message="slack_delivery_pending",
            created_at="2026-05-16T11:59:00+00:00",
        )
    )
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
        clock=lambda: now,
    )

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )

    assert sent == []
    assert result.id == existing.id
    assert result.status == "failed"
    assert result.error_message == "slack_delivery_pending"
    assert result.deduped is True


def test_existing_pending_reservation_with_disabled_slack_stays_retryable_for_later_configured_post() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    now = datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc)
    existing = repository.record_attempt(
        SlackNotificationAttempt(
            business_id="limitless",
            environment="prod",
            route=SlackNotificationRoute.HOT_LEADS,
            dedupe_key="hot-lead:lead_123",
            channel_id="CHOT",
            status="failed",
            error_message="slack_delivery_pending",
            created_at="2026-05-16T11:59:00+00:00",
        )
    )
    disabled_service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=False,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
        clock=lambda: now,
    )

    disabled_result = disabled_service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )
    after_disabled = repository.get(existing.id)
    configured_before_stale = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
        clock=lambda: now,
    )
    before_stale_result = configured_before_stale.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )
    configured_after_stale = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
        clock=lambda: datetime(2026, 5, 16, 12, 10, tzinfo=timezone.utc),
    )
    after_stale_result = configured_after_stale.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )

    assert sent == [
        {
            "endpoint": "https://slack.com/api/chat.postMessage",
            "headers": {
                "Authorization": "Bearer xoxb-test",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            "payload": {
                "channel": "CHOT",
                "text": "Hot lead",
                "blocks": [],
                "unfurl_links": False,
                "unfurl_media": False,
            },
        }
    ]
    assert disabled_result.id == existing.id
    assert disabled_result.status == "failed"
    assert disabled_result.error_message == "slack_delivery_pending"
    assert after_disabled is not None
    assert after_disabled.id == existing.id
    assert after_disabled.status == "failed"
    assert after_disabled.error_message == "slack_delivery_pending"
    assert before_stale_result.id == existing.id
    assert before_stale_result.status == "failed"
    assert before_stale_result.deduped is True
    assert after_stale_result.id == existing.id
    assert after_stale_result.status == "sent"


def test_race_duplicate_pending_reservation_dedupes_without_posting() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    pending = SlackNotificationAttempt(
        business_id="limitless",
        environment="prod",
        route=SlackNotificationRoute.HOT_LEADS,
        dedupe_key="hot-lead:lead_123",
        channel_id="CHOT",
        status="failed",
        error_message="slack_delivery_pending",
    )

    def duplicate_pending_reservation(**_kwargs: Any) -> SlackNotificationAttempt:
        return pending.model_copy(update={"deduped": True})

    repository.reserve_attempt_for_delivery = duplicate_pending_reservation  # type: ignore[method-assign]
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
    )

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )

    assert sent == []
    assert result.id == pending.id
    assert result.status == "failed"
    assert result.error_message == "slack_delivery_pending"
    assert result.deduped is True


def test_nested_notify_while_first_delivery_is_in_flight_posts_once() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    nested_results: list[SlackNotificationAttempt] = []
    nested_started = False
    service_holder: dict[str, SlackNotificationService] = {}

    def sender(outbound_request: dict[str, Any]) -> dict[str, Any]:
        nonlocal nested_started
        sent.append(outbound_request)
        if not nested_started:
            nested_started = True
            nested_results.append(
                service_holder["service"].notify(
                    route=SlackNotificationRoute.HOT_LEADS,
                    business_id="limitless",
                    environment="prod",
                    dedupe_key="hot-lead:lead_123",
                    text="Hot lead replay",
                    blocks=[],
                )
            )
        return {"ok": True, "channel": outbound_request["payload"]["channel"], "ts": "1715788800.000100"}

    service = SlackNotificationService(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        request_sender=sender,
        clock=lambda: datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
    )
    service_holder["service"] = service

    result = service.notify(
        route=SlackNotificationRoute.HOT_LEADS,
        business_id="limitless",
        environment="prod",
        dedupe_key="hot-lead:lead_123",
        text="Hot lead",
        blocks=[],
    )

    assert len(sent) == 1
    assert result.status == "sent"
    assert len(nested_results) == 1
    assert nested_results[0].deduped is True
    assert nested_results[0].status == "failed"
    assert nested_results[0].error_message == "slack_delivery_pending"


def test_successful_slack_send_persistence_failure_is_not_rewritten_as_delivery_failure() -> None:
    sent: list[dict[str, Any]] = []
    repository = build_repository()
    update_statuses: list[str] = []
    original_update_attempt = repository.update_attempt

    def failing_update(attempt: SlackNotificationAttempt) -> SlackNotificationAttempt:
        update_statuses.append(attempt.status)
        if attempt.status == "sent":
            raise RuntimeError("database unavailable")
        raise AssertionError("provider success persistence failure must not be rewritten as Slack failure")

    repository.update_attempt = failing_update  # type: ignore[method-assign]
    service = build_service(
        settings=Settings(
            _env_file=None,
            slack_notifications_enabled=True,
            slack_bot_token="xoxb-test",
            slack_channel_hot_leads="CHOT",
        ),
        repository=repository,
        sent=sent,
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.notify(
            route=SlackNotificationRoute.HOT_LEADS,
            business_id="limitless",
            environment="prod",
            dedupe_key="hot-lead:lead_123",
            text="Hot lead",
            blocks=[],
        )

    repository.update_attempt = original_update_attempt  # type: ignore[method-assign]
    assert len(sent) == 1
    assert update_statuses == ["sent"]
