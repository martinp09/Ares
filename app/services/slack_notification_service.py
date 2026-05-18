from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable
from urllib import request

from app.core.config import Settings, get_settings
from app.db.slack_notifications import SlackNotificationsRepository
from app.models.commands import utc_now
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute

RequestSender = Callable[[dict[str, Any]], dict[str, Any] | None]
Clock = Callable[[], datetime]
RETRYABLE_DELIVERY_PENDING = "slack_delivery_pending"


class SlackNotificationService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        repository: SlackNotificationsRepository | None = None,
        request_sender: RequestSender | None = None,
        clock: Clock | None = None,
        pending_retry_after_seconds: int = 300,
    ) -> None:
        self.settings = settings or get_settings()
        self.repository = repository or SlackNotificationsRepository(settings=self.settings)
        self.request_sender = request_sender or _default_sender
        self.clock = clock or (lambda: utc_now())
        self.pending_retry_after_seconds = pending_retry_after_seconds

    def notify(
        self,
        route: SlackNotificationRoute | str,
        business_id: str,
        environment: str,
        dedupe_key: str,
        text: str,
        blocks: list[dict[str, Any]],
        payload: dict[str, Any] | None = None,
    ) -> SlackNotificationAttempt:
        resolved_route = SlackNotificationRoute(route)
        channel_id = self._channel_for(resolved_route)
        skip_reason = self._skip_reason(channel_id)
        if skip_reason is not None:
            existing = self.repository.get_by_dedupe_key(
                business_id=business_id,
                environment=environment,
                route=resolved_route,
                dedupe_key=dedupe_key,
            )
            if existing is not None:
                return existing.model_copy(update={"deduped": True})
            skipped = SlackNotificationAttempt(
                business_id=business_id,
                environment=environment,
                route=resolved_route,
                dedupe_key=dedupe_key,
                channel_id=channel_id,
                status="skipped",
                payload=payload or {},
                error_message=skip_reason,
            )
            return self.repository.record_attempt(skipped)

        recorded = self.repository.reserve_attempt_for_delivery(
            business_id=business_id,
            environment=environment,
            route=resolved_route,
            dedupe_key=dedupe_key,
            channel_id=channel_id,
            payload=payload or {},
            now=self.clock().isoformat(),
            pending_retry_after_seconds=self.pending_retry_after_seconds,
            retryable_error_message=RETRYABLE_DELIVERY_PENDING,
        )
        if recorded.deduped:
            return recorded

        try:
            response = self.request_sender(
                {
                    "endpoint": "https://slack.com/api/chat.postMessage",
                    "headers": {
                        "Authorization": f"Bearer {self.settings.slack_bot_token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    "payload": {
                        "channel": channel_id,
                        "text": text,
                        "blocks": blocks,
                        "unfurl_links": False,
                        "unfurl_media": False,
                    },
                }
            ) or {}
        except Exception as exc:
            return self.repository.update_attempt(
                recorded.model_copy(update={"status": "failed", "error_message": str(exc), "sent_at": None})
            )

        if response.get("ok") is False:
            return self.repository.update_attempt(
                recorded.model_copy(
                    update={
                        "status": "failed",
                        "error_message": str(response.get("error") or "Slack notification failed"),
                        "sent_at": None,
                    }
                )
            )

        return self.repository.update_attempt(
            recorded.model_copy(
                update={
                    "status": "sent",
                    "slack_message_ts": str(response["ts"]) if response.get("ts") else None,
                    "error_message": None,
                    "sent_at": self.clock().isoformat(),
                }
            )
        )

    def _skip_reason(self, channel_id: str | None) -> str | None:
        if not self.settings.slack_notifications_enabled:
            return "slack_notifications_disabled"
        if not self.settings.slack_bot_token:
            return "slack_bot_token_missing"
        if not channel_id:
            return "slack_channel_not_configured"
        return None

    def _channel_for(self, route: SlackNotificationRoute) -> str | None:
        if route == SlackNotificationRoute.LEAD_RUNS:
            return self.settings.slack_channel_lead_runs or self.settings.slack_channel_leads
        if route == SlackNotificationRoute.HOT_LEADS:
            return self.settings.slack_channel_hot_leads
        if route == SlackNotificationRoute.CHIEF_OF_STAFF_DIGEST:
            return self.settings.slack_channel_chief_of_staff
        if route == SlackNotificationRoute.INSTANTLY_REPLIES:
            return self.settings.slack_channel_instantly_replies
        if route == SlackNotificationRoute.LEASE_OPTION_INBOUND:
            return self.settings.slack_channel_lease_option_inbound or self.settings.slack_channel_intake
        if route == SlackNotificationRoute.SMS_CALLS:
            return self.settings.slack_channel_sms_calls
        if route == SlackNotificationRoute.ERRORS:
            return self.settings.slack_channel_errors
        raise ValueError(f"Unsupported Slack notification route: {route}")


def _default_sender(outbound_request: dict[str, Any]) -> dict[str, Any] | None:
    body = json.dumps(outbound_request["payload"]).encode("utf-8")
    req = request.Request(
        outbound_request["endpoint"],
        data=body,
        headers=outbound_request["headers"],
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:  # nosec B310
        raw = response.read()
    return json.loads(raw.decode("utf-8")) if raw else None


slack_notification_service = SlackNotificationService()
