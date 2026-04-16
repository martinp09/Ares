from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Iterator, Mapping
from urllib import error, parse, request

from app.models.providers import ProviderTransportError
from app.services.provider_retry_service import ProviderRetryService

_DEFAULT_BASE_URL = "https://api.instantly.ai"
_DEFAULT_BATCH_SIZE = 100
_DEFAULT_BATCH_WAIT_SECONDS = 0.25
_MAX_BULK_ADD_SIZE = 1000

INSTANTLY_EVENT_MAP: dict[str, str] = {
    "email_sent": "lead.email.sent",
    "email_opened": "lead.email.opened",
    "reply_received": "lead.reply.received",
    "auto_reply_received": "lead.reply.auto_received",
    "link_clicked": "lead.email.clicked",
    "email_bounced": "lead.email.bounced",
    "lead_unsubscribed": "lead.suppressed.unsubscribe",
    "account_error": "provider.account_error",
    "campaign_completed": "campaign.completed",
    "lead_neutral": "lead.status.neutral",
    "lead_interested": "lead.status.interested",
    "lead_not_interested": "lead.status.not_interested",
    "lead_meeting_booked": "lead.meeting.booked",
    "lead_meeting_completed": "lead.meeting.completed",
    "lead_closed": "lead.status.closed",
    "lead_out_of_office": "lead.status.out_of_office",
    "lead_wrong_person": "lead.status.wrong_person",
}

RequestSender = Callable[[dict[str, Any]], Any]


def _masked_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def build_authorization_header(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def build_instantly_request(
    *,
    api_key: str,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    base_url: str = _DEFAULT_BASE_URL,
) -> dict[str, Any]:
    normalized_path = path if path.startswith("/") else f"/{path}"
    endpoint = f"{base_url.rstrip('/')}{normalized_path}"
    if query:
        encoded = parse.urlencode({key: value for key, value in query.items() if value is not None}, doseq=True)
        if encoded:
            endpoint = f"{endpoint}?{encoded}"
    return {
        "method": method.upper(),
        "endpoint": endpoint,
        "headers": {
            **build_authorization_header(api_key),
            "Content-Type": "application/json",
        },
        "payload": dict(payload or {}),
    }


def parse_instantly_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(UTC)
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def canonical_event_type_for(raw_event_type: str | None) -> str:
    normalized = str(raw_event_type or "").strip()
    if normalized in INSTANTLY_EVENT_MAP:
        return INSTANTLY_EVENT_MAP[normalized]
    if normalized:
        return "lead.label.custom"
    return "provider.unknown"


def build_webhook_idempotency_key(payload: Mapping[str, Any]) -> str:
    stable_bits = [
        str(payload.get("id") or ""),
        str(payload.get("event_id") or ""),
        str(payload.get("event_type") or ""),
        str(payload.get("timestamp") or ""),
        str(payload.get("workspace") or ""),
        str(payload.get("campaign_id") or ""),
        str(payload.get("lead_email") or ""),
        str(payload.get("email_id") or ""),
        str(payload.get("step") or ""),
        str(payload.get("variant") or ""),
    ]
    digest = hashlib.sha256("|".join(stable_bits).encode("utf-8")).hexdigest()
    return f"instantly-webhook:{digest}"


def normalize_webhook_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_event_type = str(payload.get("event_type") or "").strip()
    canonical_event_type = canonical_event_type_for(raw_event_type)
    occurred_at = parse_instantly_timestamp(payload.get("timestamp"))
    metadata = {
        "workspace": payload.get("workspace"),
        "campaign_name": payload.get("campaign_name"),
        "email_account": payload.get("email_account"),
        "unibox_url": payload.get("unibox_url"),
        "step": payload.get("step"),
        "variant": payload.get("variant"),
        "is_first": payload.get("is_first"),
        "email_subject": payload.get("email_subject"),
        "email_text": payload.get("email_text"),
        "email_html": payload.get("email_html"),
        "reply_text": payload.get("reply_text"),
        "reply_html": payload.get("reply_html"),
        "provider_payload": dict(payload),
    }
    return {
        "provider": "instantly",
        "provider_event_id": payload.get("id") or payload.get("event_id") or payload.get("email_id"),
        "provider_event_type": raw_event_type or "unknown",
        "provider_email_id": payload.get("email_id"),
        "canonical_event_type": canonical_event_type,
        "campaign_id": payload.get("campaign_id"),
        "campaign_name": payload.get("campaign_name"),
        "lead_email": payload.get("lead_email"),
        "occurred_at": occurred_at,
        "idempotency_key": build_webhook_idempotency_key(payload),
        "metadata": metadata,
    }


class InstantlyClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        request_sender: RequestSender | None = None,
        retry_service: ProviderRetryService | None = None,
        batch_size: int = _DEFAULT_BATCH_SIZE,
        batch_wait_seconds: float = _DEFAULT_BATCH_WAIT_SECONDS,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.request_sender = request_sender or self._default_request_sender
        self.retry_service = retry_service or ProviderRetryService()
        self.batch_size = max(1, min(batch_size, _MAX_BULK_ADD_SIZE))
        self.batch_wait_seconds = max(0.0, batch_wait_seconds)
        self.sleep_fn = sleep_fn or time.sleep

    def __repr__(self) -> str:
        return (
            "InstantlyClient("
            f"base_url='{self.base_url}', api_key='{_masked_secret(self.api_key)}', "
            f"batch_size={self.batch_size}, batch_wait_seconds={self.batch_wait_seconds}"
            ")"
        )

    def create_campaign(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/campaigns", payload=payload)

    def list_campaigns(self, **query: Any) -> dict[str, Any]:
        return self._send("GET", "/api/v2/campaigns", query=query)

    def iter_campaigns(self, **query: Any) -> Iterator[dict[str, Any]]:
        yield from self._iter_cursor("/api/v2/campaigns", **query)

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        return self._send("GET", f"/api/v2/campaigns/{campaign_id}")

    def update_campaign(self, campaign_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("PATCH", f"/api/v2/campaigns/{campaign_id}", payload=payload)

    def delete_campaign(self, campaign_id: str) -> dict[str, Any]:
        return self._send("DELETE", f"/api/v2/campaigns/{campaign_id}")

    def activate_campaign(self, campaign_id: str) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/campaigns/{campaign_id}/activate")

    def pause_campaign(self, campaign_id: str) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/campaigns/{campaign_id}/pause")

    def resume_campaign(self, campaign_id: str) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/campaigns/{campaign_id}/resume")

    def search_campaigns_by_lead_email(self, email: str) -> dict[str, Any]:
        return self._send("GET", "/api/v2/campaigns/search", query={"lead_email": email})

    def share_campaign(self, campaign_id: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/campaigns/{campaign_id}/share", payload=payload)

    def create_campaign_from_shared(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/campaigns/shared", payload=payload)

    def export_campaign_json(self, campaign_id: str) -> dict[str, Any]:
        return self._send("GET", f"/api/v2/campaigns/{campaign_id}/export")

    def duplicate_campaign(self, campaign_id: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/campaigns/{campaign_id}/duplicate", payload=payload)

    def get_launched_campaigns_count(self) -> dict[str, Any]:
        return self._send("GET", "/api/v2/campaigns/launched/count")

    def add_campaign_variables(self, campaign_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/campaigns/{campaign_id}/variables", payload=payload)

    def get_campaign_sending_status(self, campaign_id: str) -> dict[str, Any]:
        return self._send("GET", f"/api/v2/campaigns/{campaign_id}/sending-status")

    def create_lead(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/leads", payload=payload)

    def list_leads(self, **query: Any) -> dict[str, Any]:
        return self._send("GET", "/api/v2/leads", query=query)

    def iter_leads(self, **query: Any) -> Iterator[dict[str, Any]]:
        yield from self._iter_cursor("/api/v2/leads", **query)

    def get_lead(self, lead_id: str) -> dict[str, Any]:
        return self._send("GET", f"/api/v2/leads/{lead_id}")

    def update_lead(self, lead_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("PATCH", f"/api/v2/leads/{lead_id}", payload=payload)

    def delete_lead(self, lead_id: str) -> dict[str, Any]:
        return self._send("DELETE", f"/api/v2/leads/{lead_id}")

    def bulk_delete_leads(self, lead_ids: Iterable[str]) -> dict[str, Any]:
        ids = [lead_id for lead_id in lead_ids if lead_id]
        return self._send("POST", "/api/v2/leads/delete", payload={"lead_ids": ids})

    def bulk_add_leads(
        self,
        leads: list[Mapping[str, Any]],
        *,
        campaign_id: str | None = None,
        list_id: str | None = None,
        skip_if_in_workspace: bool = True,
        skip_if_in_campaign: bool = True,
        skip_if_in_list: bool = True,
        blocklist_id: str | None = None,
        assigned_to: str | None = None,
        verify_leads_on_import: bool = False,
        chunk_size: int | None = None,
        wait_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        if not leads:
            raise ValueError("at least one lead is required")
        if campaign_id and list_id:
            raise ValueError("bulk add accepts campaign_id or list_id, not both")
        effective_chunk_size = max(1, min(chunk_size or self.batch_size, _MAX_BULK_ADD_SIZE))
        effective_wait_seconds = self.batch_wait_seconds if wait_seconds is None else max(0.0, wait_seconds)
        results: list[dict[str, Any]] = []
        for index, chunk in enumerate(self._chunks(leads, effective_chunk_size)):
            payload = {
                "leads": [dict(lead) for lead in chunk],
                "campaign_id": campaign_id,
                "list_id": list_id,
                "skip_if_in_workspace": skip_if_in_workspace,
                "skip_if_in_campaign": skip_if_in_campaign,
                "skip_if_in_list": skip_if_in_list,
                "blocklist_id": blocklist_id,
                "assigned_to": assigned_to,
                "verify_leads_on_import": verify_leads_on_import,
            }
            results.append(self._send("POST", "/api/v2/leads/add", payload=payload))
            if index < max(0, len(leads) - 1) and len(chunk) == effective_chunk_size and index < (len(leads) - 1) // effective_chunk_size:
                self.sleep_fn(effective_wait_seconds)
        return results

    def merge_leads(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/leads/merge", payload=payload)

    def move_leads(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/leads/move", payload=payload)

    def bulk_assign_leads(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/leads/assign", payload=payload)

    def update_interest_status(self, lead_id: str, *, lt_interest_status: str) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/leads/{lead_id}/interest-status", payload={"lt_interest_status": lt_interest_status})

    def remove_lead_from_subsequence(self, lead_id: str) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/leads/{lead_id}/subsequence/remove")

    def move_lead_to_subsequence(self, lead_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/leads/{lead_id}/subsequence/move", payload=payload)

    def get_account_campaign_mappings(self, email: str) -> dict[str, Any]:
        return self._send("GET", f"/api/v2/account-campaign-mappings/{parse.quote(email, safe='@')}")

    def list_webhooks(self, **query: Any) -> dict[str, Any]:
        return self._send("GET", "/api/v2/webhooks", query=query)

    def create_webhook(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/api/v2/webhooks", payload=payload)

    def get_webhook(self, webhook_id: str) -> dict[str, Any]:
        return self._send("GET", f"/api/v2/webhooks/{webhook_id}")

    def update_webhook(self, webhook_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._send("PATCH", f"/api/v2/webhooks/{webhook_id}", payload=payload)

    def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        return self._send("DELETE", f"/api/v2/webhooks/{webhook_id}")

    def list_webhook_event_types(self) -> dict[str, Any]:
        return self._send("GET", "/api/v2/webhooks/event-types")

    def test_webhook(self, webhook_id: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/webhooks/{webhook_id}/test", payload=payload)

    def resume_webhook(self, webhook_id: str) -> dict[str, Any]:
        return self._send("POST", f"/api/v2/webhooks/{webhook_id}/resume")

    def _iter_cursor(self, path: str, **query: Any) -> Iterator[dict[str, Any]]:
        next_cursor = query.pop("starting_after", None)
        while True:
            page = self._send("GET", path, query={**query, "starting_after": next_cursor} if next_cursor else query)
            for item in page.get("items") or page.get("data") or []:
                yield item
            next_cursor = page.get("next_starting_after")
            if not next_cursor:
                break

    def _send(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_payload = build_instantly_request(
            api_key=self.api_key,
            method=method,
            path=path,
            payload=payload,
            query=query,
            base_url=self.base_url,
        )
        attempt = 0
        while True:
            attempt += 1
            try:
                raw_response = self.request_sender(request_payload)
                if raw_response is None:
                    return {}
                if isinstance(raw_response, dict):
                    return raw_response
                if isinstance(raw_response, list):
                    return {"items": raw_response}
                raise ProviderTransportError(
                    f"Instantly transport returned unsupported response type for {method.upper()} {path}",
                )
            except Exception as exc:  # noqa: BLE001
                if not isinstance(exc, ProviderTransportError):
                    exc = ProviderTransportError(f"Instantly transport failed for {method.upper()} {path}: {exc}")
                retry_state = self.retry_service.evaluate(attempt, exc)
                if retry_state.exhausted:
                    raise exc
                self.sleep_fn(self._retry_delay_seconds(exc, retry_state.next_delay_seconds))

    @staticmethod
    def _chunks(items: list[Mapping[str, Any]], chunk_size: int) -> Iterator[list[Mapping[str, Any]]]:
        for index in range(0, len(items), chunk_size):
            yield items[index : index + chunk_size]

    @staticmethod
    def _retry_delay_seconds(exc: ProviderTransportError, fallback_delay: float | None) -> float:
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                return max(0.0, fallback_delay or 0.0)
        return max(0.0, fallback_delay or 0.0)

    @staticmethod
    def _default_request_sender(outbound_request: dict[str, Any]) -> dict[str, Any]:
        payload = outbound_request.get("payload") or {}
        body = json.dumps(payload).encode("utf-8") if payload else None
        req = request.Request(
            outbound_request["endpoint"],
            data=body,
            headers=outbound_request.get("headers") or {},
            method=outbound_request.get("method") or "GET",
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp is not None else ""
            message = raw or f"HTTP {exc.code}"
            raise ProviderTransportError(message, status_code=exc.code, headers=dict(exc.headers.items())) from exc
        except error.URLError as exc:
            raise ProviderTransportError(str(exc.reason)) from exc
