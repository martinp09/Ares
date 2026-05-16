from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import httpx

from app.core.config import Settings, get_settings
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.sms_agent import SmsAgentRepository
from app.models.sms_agent import SmsAgentJobCreate, SmsAgentSendRequest, SmsAgentSendResponse
from app.providers.textgrid import build_outbound_sms_request, normalize_phone_number

if TYPE_CHECKING:
    from app.models.marketing_leads import MarketingLeadRecord
    from app.services.inbound_sms_service import NormalizedSmsEvent

RequestSender = Callable[[dict[str, Any]], dict[str, Any]]


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {"message": response.text}
    return payload if isinstance(payload, dict) else {"data": payload}


def _extract_error(payload: dict[str, Any], response: httpx.Response) -> str:
    for key in ("message", "Message", "error", "detail", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            for key in ("message", "detail", "description"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    if response.text.strip():
        return response.text.strip()
    return f"TextGrid request failed with HTTP {response.status_code}"


def _extract_provider_message_id(response: dict[str, Any]) -> str | None:
    for key in ("sid", "messageSid", "MessageSid", "message_id", "id", "provider_message_id"):
        value = response.get(key)
        if value:
            return str(value)
    return None


def _extract_provider_status(response: dict[str, Any]) -> str:
    raw = str(response.get("status") or response.get("MessageStatus") or "queued").lower()
    return raw if raw in {"queued", "sent", "delivered", "failed"} else "queued"


class SmsAgentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        conversations: ConversationsRepository | None = None,
        messages: MessagesRepository | None = None,
        sms_agent_repository: SmsAgentRepository | None = None,
        request_sender: RequestSender | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.conversations = conversations or ConversationsRepository(settings=self.settings)
        self.messages = messages or MessagesRepository(settings=self.settings)
        self.sms_agent_repository = sms_agent_repository or SmsAgentRepository(settings=self.settings)
        self.request_sender = request_sender or self._send_textgrid_request

    def enqueue_inbound_reply_job(
        self,
        *,
        event: NormalizedSmsEvent,
        lead: MarketingLeadRecord | None,
        provider_thread_id: str | None,
        receipt_id: str | None,
    ) -> str | None:
        if event.event_type != "inbound" or lead is None:
            return None
        business_id = lead.business_id
        environment = lead.environment
        if not business_id or not environment:
            return None
        job = self.sms_agent_repository.enqueue_job(
            SmsAgentJobCreate(
                business_id=business_id,
                environment=environment,
                provider_webhook_id=receipt_id,
                conversation_id=provider_thread_id,
                contact_id=lead.id,
                from_number=event.from_number,
                to_number=event.to_number,
                metadata={
                    "external_id": event.external_id,
                    "body_preview": event.body[:160],
                },
            )
        )
        return job.id

    def send_message(self, request: SmsAgentSendRequest) -> SmsAgentSendResponse:
        normalized_to = normalize_phone_number(request.to)
        from_identity = normalize_phone_number(self.settings.textgrid_from_number) if self.settings.textgrid_from_number else None
        dry_run = request.dry_run_only or not self.settings.provider_live_sends_enabled
        if dry_run:
            return SmsAgentSendResponse(
                status="skipped",
                to=normalized_to,
                from_identity=from_identity,
                dry_run=True,
                log_status="skipped_dry_run",
            )

        self._require_textgrid_config()
        if not request.contact_id:
            raise RuntimeError("contact_id is required for live SMS sends")
        if not request.sms_consent_confirmed:
            raise RuntimeError("sms_consent_confirmed is required for live SMS sends")
        outbound_request = build_outbound_sms_request(
            account_sid=str(self.settings.textgrid_account_sid),
            auth_token=str(self.settings.textgrid_auth_token),
            from_number=str(self.settings.textgrid_from_number),
            to_number=normalized_to,
            body=request.body,
            base_url=self.settings.textgrid_base_url,
            status_callback_url=self.settings.textgrid_status_callback_url,
        )
        if self.settings.textgrid_sms_url:
            outbound_request["endpoint"] = self.settings.textgrid_sms_url

        provider_response = self.request_sender(outbound_request)
        provider_message_id = _extract_provider_message_id(provider_response)
        provider_status = _extract_provider_status(provider_response)
        message_id: str | None = None
        conversation_id: str | None = None
        log_status = "skipped_no_contact_id"

        if request.contact_id:
            provider_thread_id = request.conversation_id or provider_message_id or normalized_to
            conversation = self.conversations.get_or_create(
                business_id=request.business_id,
                environment=request.environment,
                contact_id=request.contact_id,
                channel="sms",
                provider_thread_id=provider_thread_id,
            )
            conversation_id = conversation.provider_thread_id
            message = self.messages.append_outbound(
                business_id=request.business_id,
                environment=request.environment,
                contact_id=request.contact_id,
                conversation_id=conversation_id,
                channel="sms",
                provider="textgrid",
                external_message_id=provider_message_id,
                body=request.body,
                metadata={
                    "sms_agent": True,
                    "provider_status": provider_status,
                    **request.metadata,
                },
            )
            message_id = message.id
            log_status = "logged"

        return SmsAgentSendResponse(
            status=provider_status,
            to=normalized_to,
            from_identity=from_identity,
            message_id=message_id,
            conversation_id=conversation_id,
            provider_message_id=provider_message_id,
            dry_run=False,
            log_status=log_status,
        )

    def _require_textgrid_config(self) -> None:
        missing = [
            name
            for name, value in (
                ("TEXTGRID_ACCOUNT_SID", self.settings.textgrid_account_sid),
                ("TEXTGRID_AUTH_TOKEN", self.settings.textgrid_auth_token),
                ("TEXTGRID_FROM_NUMBER", self.settings.textgrid_from_number),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing TextGrid config: {', '.join(missing)}")

    def _send_textgrid_request(self, outbound_request: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            str(outbound_request["endpoint"]),
            headers=dict(outbound_request["headers"]),
            data=dict(outbound_request["payload"]),
            timeout=self.settings.provider_request_timeout_seconds,
        )
        payload = _safe_json(response)
        if response.is_error:
            raise RuntimeError(_extract_error(payload, response))
        return payload
