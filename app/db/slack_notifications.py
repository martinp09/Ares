from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib import error as url_error

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, InMemoryControlPlaneClient
from app.db.control_plane_supabase import control_plane_backend_enabled, fetch_rows, insert_rows, patch_rows, resolve_tenant
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute


class SlackNotificationsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._force_memory = client is not None and getattr(client, "backend", "memory") != "supabase"
        self._supabase_enabled = (
            control_plane_backend_enabled(self.settings)
            and bool(self.settings.supabase_url)
            and bool(self.settings.supabase_service_role_key)
            and not self._force_memory
        )
        self.client = client or InMemoryControlPlaneClient()

    def record_attempt(self, attempt: SlackNotificationAttempt) -> SlackNotificationAttempt:
        if self._supabase_enabled:
            return self._record_attempt_in_supabase(attempt)

        route_value = self._route_value(attempt.route)
        lookup_key = (attempt.business_id, attempt.environment, route_value, attempt.dedupe_key)
        with self.client.transaction() as store:
            existing_id = store.slack_notification_keys.get(lookup_key)
            if existing_id is not None:
                return store.slack_notifications[existing_id].model_copy(update={"deduped": True})
            store.slack_notifications[attempt.id] = attempt
            store.slack_notification_keys[lookup_key] = attempt.id
            return attempt

    def update_attempt(self, attempt: SlackNotificationAttempt) -> SlackNotificationAttempt:
        if self._supabase_enabled:
            tenant = resolve_tenant(attempt.business_id, attempt.environment, settings=self.settings)
            rows = patch_rows(
                "slack_notifications",
                params={
                    "id": f"eq.{attempt.id}",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                },
                row=self._update_payload_for_supabase(attempt),
                select="*",
                settings=self.settings,
            )
            if not rows:
                raise KeyError(f"Slack notification attempt not found: {attempt.id}")
            return self._record_from_supabase(rows[0])

        route_value = self._route_value(attempt.route)
        lookup_key = (attempt.business_id, attempt.environment, route_value, attempt.dedupe_key)
        with self.client.transaction() as store:
            existing = store.slack_notifications.get(attempt.id)
            if existing is None:
                raise KeyError(f"Slack notification attempt not found: {attempt.id}")
            existing_key = (
                existing.business_id,
                existing.environment,
                self._route_value(existing.route),
                existing.dedupe_key,
            )
            if existing_key != lookup_key:
                store.slack_notification_keys.pop(existing_key, None)
                store.slack_notification_keys[lookup_key] = attempt.id
            store.slack_notifications[attempt.id] = attempt
            return attempt

    def reserve_attempt_for_delivery(
        self,
        *,
        business_id: str,
        environment: str,
        route: SlackNotificationRoute | str,
        dedupe_key: str,
        channel_id: str | None,
        payload: dict[str, Any],
        now: str,
        pending_retry_after_seconds: int,
        retryable_error_message: str,
    ) -> SlackNotificationAttempt:
        route_value = self._route_value(route)
        if self._supabase_enabled:
            existing = self.get_by_dedupe_key(
                business_id=business_id,
                environment=environment,
                route=route_value,
                dedupe_key=dedupe_key,
            )
            if existing is not None:
                return existing.model_copy(update={"deduped": True})
            return self.record_attempt(
                SlackNotificationAttempt(
                    business_id=business_id,
                    environment=environment,
                    route=SlackNotificationRoute(route_value),
                    dedupe_key=dedupe_key,
                    channel_id=channel_id,
                    status="failed",
                    payload=payload,
                    error_message=retryable_error_message,
                    created_at=now,
                )
            )

        lookup_key = (business_id, environment, route_value, dedupe_key)
        with self.client.transaction() as store:
            existing_id = store.slack_notification_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.slack_notifications[existing_id]
                if self._is_stale_retryable_attempt(
                    existing,
                    now=now,
                    pending_retry_after_seconds=pending_retry_after_seconds,
                    retryable_error_message=retryable_error_message,
                ):
                    claimed = existing.model_copy(
                        update={
                            "channel_id": channel_id,
                            "status": "failed",
                            "slack_message_ts": None,
                            "payload": payload,
                            "error_message": retryable_error_message,
                            "created_at": now,
                            "sent_at": None,
                            "deduped": False,
                        }
                    )
                    store.slack_notifications[existing.id] = claimed
                    return claimed
                return existing.model_copy(update={"deduped": True})

            attempt = SlackNotificationAttempt(
                business_id=business_id,
                environment=environment,
                route=SlackNotificationRoute(route_value),
                dedupe_key=dedupe_key,
                channel_id=channel_id,
                status="failed",
                payload=payload,
                error_message=retryable_error_message,
                created_at=now,
            )
            store.slack_notifications[attempt.id] = attempt
            store.slack_notification_keys[lookup_key] = attempt.id
            return attempt

    def get(
        self,
        attempt_id: str,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> SlackNotificationAttempt | None:
        if self._supabase_enabled:
            if business_id is None or environment is None:
                raise ValueError("business_id and environment are required for Supabase Slack notification reads")
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            rows = fetch_rows(
                "slack_notifications",
                params={
                    "select": "*",
                    "id": f"eq.{attempt_id}",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.slack_notifications.get(attempt_id)

    def get_by_dedupe_key(
        self,
        *,
        business_id: str,
        environment: str,
        route: SlackNotificationRoute | str,
        dedupe_key: str,
    ) -> SlackNotificationAttempt | None:
        route_value = self._route_value(route)
        if self._supabase_enabled:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            rows = fetch_rows(
                "slack_notifications",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "route": f"eq.{route_value}",
                    "dedupe_key": f"eq.{dedupe_key}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            attempt_id = store.slack_notification_keys.get((business_id, environment, route_value, dedupe_key))
            if attempt_id is None:
                return None
            return store.slack_notifications.get(attempt_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        route: SlackNotificationRoute | str | None = None,
    ) -> list[SlackNotificationAttempt]:
        if self._supabase_enabled:
            if business_id is None or environment is None:
                raise ValueError("business_id and environment are required for Supabase Slack notification reads")
            params = {"select": "*", "order": "created_at.asc,id.asc"}
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
            if route is not None:
                params["route"] = f"eq.{self._route_value(route)}"
            rows = fetch_rows("slack_notifications", params=params, settings=self.settings)
            return [self._record_from_supabase(row) for row in rows]

        with self.client.transaction() as store:
            attempts = list(store.slack_notifications.values())
        if business_id is not None:
            attempts = [attempt for attempt in attempts if attempt.business_id == business_id]
        if environment is not None:
            attempts = [attempt for attempt in attempts if attempt.environment == environment]
        if route is not None:
            route_value = self._route_value(route)
            attempts = [attempt for attempt in attempts if attempt.route.value == route_value]
        attempts.sort(
            key=lambda attempt: (
                attempt.business_id,
                attempt.environment,
                attempt.route.value,
                attempt.created_at,
                attempt.id,
            )
        )
        return attempts

    def _record_attempt_in_supabase(self, attempt: SlackNotificationAttempt) -> SlackNotificationAttempt:
        existing = self.get_by_dedupe_key(
            business_id=attempt.business_id,
            environment=attempt.environment,
            route=attempt.route,
            dedupe_key=attempt.dedupe_key,
        )
        if existing is not None:
            return existing.model_copy(update={"deduped": True})

        tenant = resolve_tenant(attempt.business_id, attempt.environment, settings=self.settings)
        try:
            row = insert_rows(
                "slack_notifications",
                [self._payload_for_supabase(attempt, business_pk=tenant.business_pk, environment=tenant.environment)],
                select="*",
                settings=self.settings,
            )[0]
        except Exception as exc:
            if not self._is_duplicate_insert_error(exc):
                raise
            refetched = self.get_by_dedupe_key(
                business_id=attempt.business_id,
                environment=attempt.environment,
                route=attempt.route,
                dedupe_key=attempt.dedupe_key,
            )
            if refetched is None:
                raise
            return refetched.model_copy(update={"deduped": True})
        return self._record_from_supabase(row)

    @staticmethod
    def _payload_for_supabase(
        attempt: SlackNotificationAttempt,
        *,
        business_pk: int,
        environment: str,
    ) -> dict[str, Any]:
        payload = attempt.model_dump(mode="json", exclude={"business_id", "environment", "deduped"})
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["route"] = attempt.route.value
        return payload

    @staticmethod
    def _update_payload_for_supabase(attempt: SlackNotificationAttempt) -> dict[str, Any]:
        return attempt.model_dump(
            mode="json",
            include={"channel_id", "status", "slack_message_ts", "payload", "error_message", "sent_at"},
        )

    @staticmethod
    def _record_from_supabase(row: dict[str, Any]) -> SlackNotificationAttempt:
        payload = dict(row)
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("route") is not None:
            payload["route"] = SlackNotificationRoute(str(row["route"]))
        return SlackNotificationAttempt.model_validate(payload)

    @staticmethod
    def _route_value(route: SlackNotificationRoute | str) -> str:
        return route.value if isinstance(route, SlackNotificationRoute) else str(route)

    @staticmethod
    def _is_stale_retryable_attempt(
        attempt: SlackNotificationAttempt,
        *,
        now: str,
        pending_retry_after_seconds: int,
        retryable_error_message: str,
    ) -> bool:
        if attempt.status != "failed" or attempt.error_message != retryable_error_message:
            return False
        try:
            created_at = datetime.fromisoformat(attempt.created_at.replace("Z", "+00:00"))
            current = datetime.fromisoformat(now.replace("Z", "+00:00"))
        except ValueError:
            return False
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return (current - created_at).total_seconds() >= pending_retry_after_seconds

    @staticmethod
    def _is_duplicate_insert_error(exc: Exception) -> bool:
        if not isinstance(exc, url_error.HTTPError):
            return False
        if exc.code == 409:
            return True
        if exc.code != 400:
            return False
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            return False
        lowered = body.lower()
        return "duplicate key" in lowered or "unique constraint" in lowered or "23505" in lowered
