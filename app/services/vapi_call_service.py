from __future__ import annotations

import hashlib
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.client import utc_now
from app.db.provider_links import ProviderLinksRepository
from app.models.calls import VoiceOutboundCallRequest
from app.models.provider_links import ProviderObjectLink
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute
from app.providers.vapi import (
    VapiClient,
    normalize_vapi_webhook_payload,
    verify_vapi_webhook_secret,
)
from app.services.slack_notification_service import slack_notification_service

_VAPI_OPERATOR_EVENT_TYPES = {
    "incoming",
    "call-ended",
    "end-of-call-report",
    "handoff",
    "human-handoff",
    "operator-handoff",
}
_VAPI_END_REPORT_SIGNALS = {"call-ended", "end-of-call-report"}
_VAPI_OPERATOR_STATUS_TOKENS = {
    "ended",
    "failed",
    "failure",
    "error",
    "errored",
    "no-answer",
    "noanswer",
    "busy",
    "canceled",
    "cancelled",
    "cancel",
    "cancellation",
    "timeout",
    "timed-out",
}
_VAPI_HANDOFF_SIGNAL_MARKERS = (
    "handoff",
    "hand-off",
    "human-handoff",
    "human handoff",
    "transfer-to-human",
    "transfer to human",
    "operator-review",
    "operator review",
    "needs-operator",
    "needs operator",
    "live-operator",
    "live operator",
)
_VAPI_TEXT_SNIPPET_LIMIT = 280
_VAPI_CONTEXT_SNIPPET_LIMIT = 220


class VapiCallService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        provider_links: ProviderLinksRepository | None = None,
        slack_notifier: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.provider_links = provider_links
        self.slack_notifier = slack_notifier or slack_notification_service

    def list_assistants_preview(self) -> dict[str, Any]:
        warnings = ["Phase 6 list route is config-only; no Vapi provider call was made."]
        default_id = self.settings.vapi_default_assistant_id or None
        if not default_id:
            warnings.append("No VAPI_DEFAULT_ASSISTANT_ID is configured.")
        return {
            "provider": "vapi",
            "resource": "assistants",
            "dry_run": True,
            "would_call_provider": False,
            "configured": bool(default_id),
            "default_id": default_id,
            "live_enabled": self._live_enabled(),
            "warnings": warnings,
        }

    def list_phone_numbers_preview(self) -> dict[str, Any]:
        warnings = ["Phase 6 list route is config-only; no Vapi provider call was made."]
        default_id = self.settings.vapi_default_phone_number_id or None
        if not default_id:
            warnings.append("No VAPI_DEFAULT_PHONE_NUMBER_ID is configured.")
        return {
            "provider": "vapi",
            "resource": "phone_numbers",
            "dry_run": True,
            "would_call_provider": False,
            "configured": bool(default_id),
            "default_id": default_id,
            "live_enabled": self._live_enabled(),
            "warnings": warnings,
        }

    def preview_outbound_call(self, request: VoiceOutboundCallRequest) -> dict[str, Any]:
        warnings = ["Dry-run preview only; no Vapi provider call or provider-link write was made."]
        payload = self._build_payload(request)
        return {
            "provider": "vapi",
            "dry_run": True,
            "would_call_provider": False,
            "live_applied": False,
            "action": "preview",
            "call_id": None,
            "provider_call_id": None,
            "provider_link_id": None,
            "payload": payload,
            "warnings": warnings,
            "error_message": None,
        }

    def dispatch_outbound_call(self, request: VoiceOutboundCallRequest) -> dict[str, Any]:
        self._require_dispatch_preflight(request)
        if self.client is None:
            self.client = VapiClient(api_key=self._api_key(), base_url=self.settings.vapi_base_url)
        if self.provider_links is None:
            self.provider_links = ProviderLinksRepository(settings=self.settings)

        payload = self._build_payload(request)
        ares_object_type, ares_object_id = self._ares_identity(request)
        existing_link = self.provider_links.get_by_ares_object(
            business_id=request.business_id,
            environment=request.environment,
            provider="vapi",
            ares_object_type=ares_object_type,
            ares_object_id=ares_object_id,
            provider_object_type="call",
        )
        if existing_link is not None:
            return {
                "provider": "vapi",
                "dry_run": False,
                "would_call_provider": False,
                "live_applied": False,
                "action": "skip",
                "call_id": existing_link.provider_object_id,
                "provider_call_id": existing_link.provider_object_id,
                "provider_link_id": existing_link.id,
                "payload": self._live_payload_summary(payload),
                "warnings": ["Existing Vapi call provider link found for Ares object; duplicate outbound call skipped."],
                "error_message": None,
            }

        try:
            provider_result = self.client.create_outbound_call(payload)
            provider_call_id = self._extract_provider_call_id(provider_result)
            provider_link_id = None
            action = "dispatched"
            warnings: list[str] = []
            if provider_call_id:
                link = self.provider_links.upsert_link(
                    ProviderObjectLink(
                        business_id=request.business_id,
                        environment=request.environment,
                        provider="vapi",
                        provider_object_type="call",
                        provider_object_id=provider_call_id,
                        ares_object_type=ares_object_type,
                        ares_object_id=ares_object_id,
                        sync_hash=request.sync_hash,
                        last_synced_at=utc_now(),
                        raw_payload={"source": "vapi_outbound_call_dispatch"},
                    )
                )
                provider_link_id = link.id
            else:
                action = "submitted_unlinked"
                warnings.append("Vapi response did not include a call id; provider link was not written.")
            return {
                "provider": "vapi",
                "dry_run": False,
                "would_call_provider": True,
                "live_applied": True,
                "action": action,
                "call_id": provider_call_id,
                "provider_call_id": provider_call_id,
                "provider_link_id": provider_link_id,
                "payload": self._live_payload_summary(payload),
                "warnings": warnings,
                "error_message": None,
            }
        except Exception as exc:  # noqa: BLE001
            safe_error = self._safe_error_message(exc, request=request, payload=payload)
            return {
                "provider": "vapi",
                "dry_run": False,
                "would_call_provider": True,
                "live_applied": False,
                "action": "error",
                "call_id": None,
                "provider_call_id": None,
                "provider_link_id": None,
                "payload": self._live_payload_summary(payload),
                "warnings": [],
                "error_message": safe_error,
            }

    def handle_webhook(self, payload: Mapping[str, Any], headers: Mapping[str, Any]) -> dict[str, Any]:
        provided_secret = self._header_value(headers, "x-vapi-secret")
        if self.settings.provider_webhook_signatures_required:
            if not verify_vapi_webhook_secret(self.settings.vapi_webhook_secret, provided_secret):
                return {
                    "accepted": False,
                    "event_type": None,
                    "provider_call_id": None,
                    "idempotency_key": None,
                    "trust_status": "rejected_bad_secret",
                    "status": None,
                    "notification": None,
                }
            trust_status = "verified_secret"
        else:
            trust_status = "unverified_accepted"
        normalized = normalize_vapi_webhook_payload(payload)
        idempotency_key = self._idempotency_key(normalized)
        notification = self._notify_webhook(
            payload=payload,
            normalized=normalized,
            idempotency_key=idempotency_key,
            trust_status=trust_status,
        )
        return {
            "accepted": True,
            "event_type": normalized.get("event_type"),
            "provider_call_id": normalized.get("provider_call_id"),
            "idempotency_key": idempotency_key,
            "trust_status": trust_status,
            "status": normalized.get("status"),
            "notification": notification,
        }

    def _notify_webhook(
        self,
        *,
        payload: Mapping[str, Any],
        normalized: Mapping[str, Any],
        idempotency_key: str,
        trust_status: str,
    ) -> dict[str, Any] | None:
        if not _vapi_webhook_should_notify(payload=payload, normalized=normalized):
            return None
        dedupe_key = f"call:{idempotency_key}"
        notification_payload = _vapi_notification_payload(
            payload=payload,
            normalized=normalized,
            route=SlackNotificationRoute.SMS_CALLS,
            dedupe_key=dedupe_key,
            trust_status=trust_status,
        )
        text = _vapi_notification_text(notification_payload)
        blocks = _vapi_notification_blocks(text=text, payload=notification_payload)
        try:
            attempt = self.slack_notifier.notify(
                route=SlackNotificationRoute.SMS_CALLS,
                business_id=str(notification_payload["business_id"]),
                environment=str(notification_payload["environment"]),
                dedupe_key=dedupe_key,
                text=text,
                blocks=blocks,
                payload=notification_payload,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "route": SlackNotificationRoute.SMS_CALLS.value,
                "status": "failed",
                "deduped": False,
                "channel_id": None,
                "dedupe_key": dedupe_key,
                "slack_message_ts": None,
                "error_message": str(exc),
            }
        return _notification_summary(attempt, route=SlackNotificationRoute.SMS_CALLS, dedupe_key=dedupe_key)

    def _require_dispatch_preflight(self, request: VoiceOutboundCallRequest) -> None:
        if not request.operator_approval:
            raise RuntimeError("Vapi outbound call requires explicit operator approval before provider calls.")
        if not self.settings.provider_live_sends_enabled:
            raise RuntimeError("Provider live sends are disabled; set PROVIDER_LIVE_SENDS_ENABLED=true before Vapi outbound calls.")
        if not self.settings.vapi_provider_live_sends_enabled:
            raise RuntimeError("Vapi live sends are disabled; set VAPI_PROVIDER_LIVE_SENDS_ENABLED=true before outbound calls.")
        if not self._api_key():
            raise RuntimeError("Vapi API key/private key is required before live outbound calls.")
        if not (request.assistant_id or self.settings.vapi_default_assistant_id):
            raise RuntimeError("Vapi assistant ID is required before live outbound calls.")
        if not (request.phone_number_id or self.settings.vapi_default_phone_number_id):
            raise RuntimeError("Vapi phone number ID is required before live outbound calls.")
        if not request.to_number.strip():
            raise RuntimeError("Vapi outbound call requires to_number.")

    def _build_payload(self, request: VoiceOutboundCallRequest) -> dict[str, Any]:
        metadata = {
            **dict(request.metadata or {}),
            "business_id": request.business_id,
            "environment": request.environment,
        }
        for key in ("crm_record_id", "opportunity_id", "task_id", "sync_hash"):
            value = getattr(request, key)
            if value not in (None, ""):
                metadata[key] = value
        payload: dict[str, Any] = {
            "assistantId": request.assistant_id or self.settings.vapi_default_assistant_id or None,
            "phoneNumberId": request.phone_number_id or self.settings.vapi_default_phone_number_id or None,
            "customer": {"number": request.to_number},
            "metadata": {key: value for key, value in metadata.items() if value not in (None, "")},
        }
        if request.customer_name:
            payload["customer"]["name"] = request.customer_name
        if request.from_number:
            payload["fromNumber"] = request.from_number
        return {key: value for key, value in payload.items() if value not in (None, "")}

    @staticmethod
    def _live_payload_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
        customer = payload.get("customer") if isinstance(payload.get("customer"), Mapping) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
        return {
            "redacted": True,
            "assistant_id_present": bool(payload.get("assistantId")),
            "phone_number_id_present": bool(payload.get("phoneNumberId")),
            "customer_number_present": bool(customer.get("number")),
            "customer_name_present": bool(customer.get("name")),
            "from_number_present": bool(payload.get("fromNumber")),
            "metadata_field_count": len(metadata),
        }

    def _api_key(self) -> str:
        return self.settings.vapi_api_key or self.settings.vapi_private_key or ""

    def _live_enabled(self) -> bool:
        return bool(self.settings.provider_live_sends_enabled and self.settings.vapi_provider_live_sends_enabled and self._api_key())

    @staticmethod
    def _ares_identity(request: VoiceOutboundCallRequest) -> tuple[str, str]:
        if request.crm_record_id:
            return "crm_record", request.crm_record_id
        if request.opportunity_id:
            return "opportunity", request.opportunity_id
        if request.task_id:
            return "task", request.task_id
        stable = hashlib.sha256(
            "|".join(
                [
                    request.business_id,
                    request.environment,
                    request.to_number,
                    request.assistant_id or "",
                    request.phone_number_id or "",
                    request.sync_hash or "",
                ]
            ).encode("utf-8")
        ).hexdigest()[:24]
        return "voice_call_request", f"vcr_{stable}"

    @staticmethod
    def _extract_provider_call_id(provider_result: Any) -> str | None:
        if not isinstance(provider_result, Mapping):
            return None
        for key in ("id", "callId", "call_id", "provider_call_id"):
            value = provider_result.get(key)
            if value not in (None, ""):
                return str(value)
        call = provider_result.get("call")
        if isinstance(call, Mapping):
            for key in ("id", "callId", "call_id"):
                value = call.get(key)
                if value not in (None, ""):
                    return str(value)
        return None

    @staticmethod
    def _header_value(headers: Mapping[str, Any], name: str) -> str | None:
        for key, value in headers.items():
            if str(key).casefold() == name.casefold():
                return str(value)
        return None

    @staticmethod
    def _idempotency_key(normalized: Mapping[str, Any]) -> str:
        base = "|".join(
            str(normalized.get(key) or "")
            for key in ("event_type", "provider_call_id", "timestamp", "message_id")
        )
        return "vapi_webhook_" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    def _safe_error_message(
        self,
        exc: Exception,
        *,
        request: VoiceOutboundCallRequest | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> str:
        _ = (exc, request, payload)
        return "Vapi provider dispatch failed."


def _vapi_notification_payload(
    *,
    payload: Mapping[str, Any],
    normalized: Mapping[str, Any],
    route: SlackNotificationRoute,
    dedupe_key: str,
    trust_status: str,
) -> dict[str, Any]:
    metadata = _mapping_value(payload, "metadata")
    call = _mapping_value(payload, "call")
    message = _mapping_value(payload, "message")
    message_call = _mapping_value(message, "call")
    customer = (
        _mapping_value(call, "customer")
        or _mapping_value(message_call, "customer")
        or _mapping_value(payload, "customer")
        or _mapping_value(message, "customer")
    )
    business_id = str(
        metadata.get("business_id")
        or call.get("business_id")
        or message_call.get("business_id")
        or message.get("business_id")
        or "unknown"
    )
    environment = str(
        metadata.get("environment")
        or call.get("environment")
        or message_call.get("environment")
        or message.get("environment")
        or "unknown"
    )
    handoff_context = _vapi_signal_context(payload, markers=_VAPI_HANDOFF_SIGNAL_MARKERS)
    tool_result_context = _vapi_tool_result_context(payload)
    return {
        "business_id": business_id,
        "environment": environment,
        "route": route.value,
        "dedupe_key": dedupe_key,
        "provider_call_id": normalized.get("provider_call_id"),
        "event_type": normalized.get("event_type"),
        "status": normalized.get("status"),
        "customer_number": _first_text(
            customer.get("number"),
            customer.get("phoneNumber"),
            customer.get("phone_number"),
            call.get("customerNumber"),
            message_call.get("customerNumber"),
            payload.get("customerNumber"),
        ),
        "customer_name": _first_text(
            customer.get("name"),
            customer.get("customerName"),
            call.get("customerName"),
            message_call.get("customerName"),
            payload.get("customerName"),
        ),
        "summary": _snippet(normalized.get("summary"), limit=_VAPI_TEXT_SNIPPET_LIMIT),
        "transcript": _snippet(normalized.get("transcript"), limit=_VAPI_TEXT_SNIPPET_LIMIT),
        "recording_url": _snippet(normalized.get("recording_url"), limit=_VAPI_CONTEXT_SNIPPET_LIMIT),
        "handoff_context": handoff_context,
        "tool_result_context": tool_result_context,
        "trust_status": trust_status,
        "next_action": "Review Vapi call event and continue the operator workflow.",
    }


def _vapi_notification_text(payload: Mapping[str, Any]) -> str:
    parts = [
        _notification_context(payload),
        (
            f"Vapi {_field_value(payload.get('event_type'))} "
            f"for call {_field_value(payload.get('provider_call_id'))}"
        ),
        f"Status: {_field_value(payload.get('status'))}",
        f"Customer: {_field_value(payload.get('customer_number'))} / {_field_value(payload.get('customer_name'))}",
        f"Trust: {_field_value(payload.get('trust_status'))}",
    ]
    for label, key in (
        ("Summary", "summary"),
        ("Transcript", "transcript"),
        ("Recording", "recording_url"),
        ("Handoff", "handoff_context"),
        ("Tool result", "tool_result_context"),
    ):
        if payload.get(key):
            parts.append(f"{label}: {_field_value(payload.get(key))}")
    parts.append(f"Next action: {_field_value(payload.get('next_action'))}")
    return " | ".join(parts)


def _vapi_notification_blocks(*, text: str, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = [
        f"*Provider call*\n{_field_value(payload.get('provider_call_id'))}",
        f"*Event / Status*\n{_field_value(payload.get('event_type'))}\n{_field_value(payload.get('status'))}",
        f"*Customer*\n{_field_value(payload.get('customer_name'))}\n{_field_value(payload.get('customer_number'))}",
        f"*Trust*\n{_field_value(payload.get('trust_status'))}",
        f"*Next action*\n{_field_value(payload.get('next_action'))}",
    ]
    for label, key in (
        ("Summary", "summary"),
        ("Transcript", "transcript"),
        ("Recording", "recording_url"),
        ("Handoff", "handoff_context"),
        ("Tool result", "tool_result_context"),
    ):
        if payload.get(key):
            fields.append(f"*{label}*\n{_field_value(payload.get(key))}")
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": _notification_context(payload)}]},
        {"type": "section", "fields": [{"type": "mrkdwn", "text": field} for field in fields]},
    ]


def _notification_summary(
    attempt: SlackNotificationAttempt | Mapping[str, Any],
    *,
    route: SlackNotificationRoute,
    dedupe_key: str,
) -> dict[str, Any]:
    payload = attempt.model_dump(mode="json") if isinstance(attempt, SlackNotificationAttempt) else dict(attempt)
    raw_route = payload.get("route")
    return {
        "route": raw_route.value if isinstance(raw_route, SlackNotificationRoute) else str(raw_route or route.value),
        "status": str(payload.get("status") or "failed"),
        "deduped": payload.get("deduped") is True,
        "channel_id": payload.get("channel_id"),
        "dedupe_key": str(payload.get("dedupe_key") or dedupe_key),
        "slack_message_ts": payload.get("slack_message_ts"),
        "error_message": payload.get("error_message"),
    }


def _notification_context(payload: Mapping[str, Any]) -> str:
    return " ".join(
        [
            f"business={_escape_slack_mrkdwn(payload.get('business_id'))}",
            f"env={_escape_slack_mrkdwn(payload.get('environment'))}",
            f"route={_escape_slack_mrkdwn(payload.get('route'))}",
            f"dedupe={_escape_slack_mrkdwn(payload.get('dedupe_key'))}",
        ]
    )


def _field_value(value: Any) -> str:
    text = _escape_slack_mrkdwn(value)
    return text or "-"


def _escape_slack_mrkdwn(value: Any) -> str:
    text = str(value or "").strip()
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value not in (None, ""):
            return str(value)
    return None


def _vapi_webhook_should_notify(*, payload: Mapping[str, Any], normalized: Mapping[str, Any]) -> bool:
    event_type = _event_token(normalized.get("event_type"))
    if event_type in _VAPI_OPERATOR_EVENT_TYPES:
        return True
    if _event_token(normalized.get("status")) in _VAPI_OPERATOR_STATUS_TOKENS:
        return True
    if _vapi_payload_has_end_report_signal(payload):
        return True
    return bool(_vapi_signal_context(payload, markers=_VAPI_HANDOFF_SIGNAL_MARKERS) or _vapi_tool_result_context(payload))


def _vapi_payload_has_end_report_signal(payload: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(payload):
        for key in ("type", "event", "event_type", "messageType", "message_type"):
            if _event_token(mapping.get(key)) in _VAPI_END_REPORT_SIGNALS:
                return True
    return False


def _vapi_signal_context(payload: Mapping[str, Any], *, markers: tuple[str, ...]) -> str | None:
    for value in _walk_values(payload):
        text = str(value)
        token = _event_token(text)
        if any(marker in token or marker in text.casefold() for marker in markers):
            return _snippet(text, limit=_VAPI_CONTEXT_SNIPPET_LIMIT)
    return None


def _vapi_tool_result_context(payload: Mapping[str, Any]) -> str | None:
    contexts: list[str] = []
    for mapping in _walk_mappings(payload):
        function = _mapping_value(mapping, "function")
        tool_name = _first_text(
            function.get("name"),
            mapping.get("name"),
            mapping.get("toolName"),
            mapping.get("tool_name"),
            mapping.get("type"),
        )
        result = _first_text(mapping.get("result"), mapping.get("output"), mapping.get("response"), mapping.get("content"))
        if tool_name and (result or _has_tool_shape(mapping)):
            context = tool_name if not result else f"{tool_name}: {result}"
            contexts.append(_snippet(context, limit=_VAPI_CONTEXT_SNIPPET_LIMIT))
        if len(contexts) >= 2:
            break
    return "; ".join(context for context in contexts if context) or None


def _has_tool_shape(mapping: Mapping[str, Any]) -> bool:
    return any(key in mapping for key in ("toolCallId", "toolCall", "toolCalls", "tool_call_id", "tool_call", "tool_calls", "function"))


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        mappings = [value]
        for child in value.values():
            mappings.extend(_walk_mappings(child))
        return mappings
    if isinstance(value, list | tuple):
        mappings: list[Mapping[str, Any]] = []
        for child in value:
            mappings.extend(_walk_mappings(child))
        return mappings
    return []


def _walk_values(value: Any) -> list[Any]:
    if isinstance(value, Mapping):
        values = list(value.keys())
        for child in value.values():
            values.extend(_walk_values(child))
        return values
    if isinstance(value, list | tuple):
        values: list[Any] = []
        for child in value:
            values.extend(_walk_values(child))
        return values
    return [value]


def _event_token(value: Any) -> str:
    return str(value or "").strip().casefold().replace("_", "-").replace(".", "-").replace(" ", "-")


def _snippet(value: Any, *, limit: int) -> str | None:
    text = " ".join(str(value or "").split())
    if not text:
        return None
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)].rstrip()}..."
