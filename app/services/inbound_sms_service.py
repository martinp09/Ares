from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Literal, Protocol
from urllib import request
from urllib.parse import urlencode

from app.core.config import Settings, get_settings
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.sequences import SequencesRepository
from app.models.lead_events import ProviderWebhookReceiptRecord
from app.models.marketing_leads import MarketingLeadRecord
from app.providers.resend import build_send_email_request
from app.providers.textgrid import build_outbound_sms_request, normalize_incoming_webhook, verify_webhook_signature


SmsAction = Literal["ignore", "qualify", "pause", "stop"]
LEASE_OPTION_SEQUENCE_KEY = "lease_option_non_booker_v1"
RequestSender = Callable[[dict[str, Any]], None]


@dataclass(slots=True)
class NormalizedSmsEvent:
    event_type: str
    body: str
    from_number: str
    to_number: str
    external_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class LeaseOptionSequenceStepRequest:
    lead_id: str
    business_id: str
    environment: str
    day: int
    channel: Literal["sms", "email"]
    template_id: str
    manual_call_checkpoint: bool = False


class TextgridWebhookAdapter(Protocol):
    def verify_signature(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        request_url: str | None = None,
    ) -> bool: ...

    def normalize(self, payload: dict[str, Any]) -> NormalizedSmsEvent: ...


class MessageRepository(Protocol):
    def append_inbound_message(self, event: NormalizedSmsEvent) -> None: ...


class SequenceReplyService(Protocol):
    def stop(self, *, phone_number: str) -> None: ...

    def pause(self, *, phone_number: str) -> None: ...


class WebhookReceiptService(Protocol):
    def record_textgrid_event(
        self,
        *,
        event: NormalizedSmsEvent,
        lead: MarketingLeadRecord | None,
        payload: dict[str, Any],
    ) -> tuple[str | None, bool]: ...

    def mark_processed(self, receipt_id: str | None) -> None: ...


class MessageLoggingHook(Protocol):
    def log_sequence_dispatch(
        self,
        *,
        lead_id: str,
        channel: Literal["sms", "email"],
        body: str,
        provider: str,
    ) -> None: ...


class _DefaultTextgridWebhookAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def verify_signature(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        request_url: str | None = None,
    ) -> bool:
        if not self.settings.textgrid_webhook_secret:
            return True
        if not request_url:
            return False
        return verify_webhook_signature(
            secret=self.settings.textgrid_webhook_secret,
            signature=signature,
            request_url=request_url,
            payload=payload,
        )

    def normalize(self, payload: dict[str, Any]) -> NormalizedSmsEvent:
        normalized = normalize_incoming_webhook(payload)
        event_type = str(normalized["type"]).replace("message.", "")
        return NormalizedSmsEvent(
            event_type=event_type,
            body=str(normalized.get("content") or ""),
            from_number=str(normalized.get("from") or ""),
            to_number=str(normalized.get("to") or ""),
            external_id=None if normalized.get("external_id") is None else str(normalized.get("external_id")),
            metadata=dict(normalized.get("metadata") or {}),
        )


class _MarketingMessageRepository:
    def __init__(
        self,
        *,
        contacts: ContactsRepository | None = None,
        conversations: ConversationsRepository | None = None,
        messages: MessagesRepository | None = None,
    ) -> None:
        self.contacts = contacts or ContactsRepository()
        self.conversations = conversations or ConversationsRepository()
        self.messages = messages or MessagesRepository()

    def append_inbound_message(self, event: NormalizedSmsEvent) -> None:
        if event.event_type != "inbound":
            return
        lead = self.contacts.find_by_phone(phone=event.from_number)
        if lead is None:
            return
        conversation = self.conversations.get_or_create(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            channel="sms",
        )
        self.messages.append_inbound(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            conversation_id=conversation.provider_thread_id,
            channel="sms",
            provider="textgrid",
            body=event.body,
        )


class _SequenceReplyAdapter:
    def __init__(
        self,
        *,
        contacts: ContactsRepository | None = None,
        sequences: SequencesRepository | None = None,
    ) -> None:
        self.contacts = contacts or ContactsRepository()
        self.sequences = sequences or SequencesRepository()

    def stop(self, *, phone_number: str) -> None:
        self._update(phone_number=phone_number, action="stop")

    def pause(self, *, phone_number: str) -> None:
        self._update(phone_number=phone_number, action="pause")

    def _update(self, *, phone_number: str, action: Literal["pause", "stop"]) -> None:
        lead = self.contacts.find_by_phone(phone=phone_number)
        if lead is None:
            return
        enrollment = self.sequences.find_active(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            sequence_key=LEASE_OPTION_SEQUENCE_KEY,
        )
        if enrollment is None:
            return
        if action == "pause":
            self.sequences.pause(
                enrollment.id,
                business_id=lead.business_id,
                environment=lead.environment,
            )
        else:
            self.sequences.stop(
                enrollment.id,
                business_id=lead.business_id,
                environment=lead.environment,
            )


class _NoopWebhookReceiptService:
    def record_textgrid_event(
        self,
        *,
        event: NormalizedSmsEvent,
        lead: MarketingLeadRecord | None,
        payload: dict[str, Any],
    ) -> tuple[str | None, bool]:
        return None, False

    def mark_processed(self, receipt_id: str | None) -> None:
        return None


class _ProviderWebhookReceiptAdapter:
    def __init__(self, provider_webhooks: ProviderWebhooksRepository | None = None) -> None:
        self.provider_webhooks = provider_webhooks or ProviderWebhooksRepository()

    def record_textgrid_event(
        self,
        *,
        event: NormalizedSmsEvent,
        lead: MarketingLeadRecord | None,
        payload: dict[str, Any],
    ) -> tuple[str | None, bool]:
        if lead is None:
            return None, False
        idempotency_seed = event.external_id or (
            f"{event.event_type}:{event.from_number}:{event.to_number}:{event.body.strip().casefold()}"
        )
        receipt = self.provider_webhooks.record(
            ProviderWebhookReceiptRecord(
                business_id=lead.business_id,
                environment=lead.environment,
                provider="textgrid",
                event_type=event.event_type,
                idempotency_key=f"textgrid:{idempotency_seed}",
                provider_event_id=event.external_id,
                provider_receipt_id=event.external_id,
                payload={"body": payload, "from": event.from_number, "to": event.to_number},
            )
        )
        return receipt.id, bool(receipt.deduped)

    def mark_processed(self, receipt_id: str | None) -> None:
        if receipt_id is None:
            return None
        self.provider_webhooks.mark_processed(receipt_id)


class _NoopMessageLoggingHook:
    def log_sequence_dispatch(
        self,
        *,
        lead_id: str,
        channel: Literal["sms", "email"],
        body: str,
        provider: str,
    ) -> None:
        return None


class _RepositoryMessageLoggingHook:
    def __init__(
        self,
        *,
        contacts: ContactsRepository | None = None,
        conversations: ConversationsRepository | None = None,
        messages: MessagesRepository | None = None,
    ) -> None:
        self.contacts = contacts or ContactsRepository()
        self.conversations = conversations or ConversationsRepository()
        self.messages = messages or MessagesRepository()

    def log_sequence_dispatch(
        self,
        *,
        lead_id: str,
        channel: Literal["sms", "email"],
        body: str,
        provider: str,
    ) -> None:
        lead = self.contacts.get_lead(lead_id)
        if lead is None:
            return
        conversation = self.conversations.get_or_create(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            channel=channel,
        )
        self.messages.append_outbound(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            conversation_id=conversation.provider_thread_id,
            channel=channel,
            provider=provider,
            body=body,
        )


class InboundSmsService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        textgrid_adapter: TextgridWebhookAdapter | None = None,
        message_repository: MessageRepository | None = None,
        sequence_service: SequenceReplyService | None = None,
        request_sender: RequestSender | None = None,
        contacts: ContactsRepository | None = None,
        webhook_receipts: WebhookReceiptService | None = None,
        message_logging_hook: MessageLoggingHook | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.textgrid_adapter = textgrid_adapter or _DefaultTextgridWebhookAdapter(self.settings)
        self.message_repository = message_repository or _MarketingMessageRepository()
        self.sequence_service = sequence_service or _SequenceReplyAdapter()
        self.request_sender = request_sender or _default_request_sender
        self.contacts = contacts or ContactsRepository()
        self.webhook_receipts = webhook_receipts or _ProviderWebhookReceiptAdapter()
        self.message_logging_hook = message_logging_hook or _RepositoryMessageLoggingHook(contacts=self.contacts)

    def handle_textgrid_webhook(
        self,
        payload: dict[str, Any],
        *,
        signature: str | None,
        request_url: str | None = None,
    ) -> dict[str, str]:
        if not self.textgrid_adapter.verify_signature(payload, signature=signature, request_url=request_url):
            raise ValueError("Invalid TextGrid webhook signature")
        event = self.textgrid_adapter.normalize(payload)
        lead = self.contacts.find_by_phone(phone=event.from_number)
        receipt_id, deduped = self.webhook_receipts.record_textgrid_event(event=event, lead=lead, payload=payload)
        if deduped:
            self.webhook_receipts.mark_processed(receipt_id)
            return {"status": "processed", "event_type": event.event_type, "action": self._decide_action(event)}
        self.message_repository.append_inbound_message(event)
        action = self._decide_action(event)
        if action == "stop":
            self.sequence_service.stop(phone_number=event.from_number)
        elif action == "pause":
            self.sequence_service.pause(phone_number=event.from_number)
        self.webhook_receipts.mark_processed(receipt_id)
        return {"status": "processed", "event_type": event.event_type, "action": action}

    def dispatch_lease_option_sequence_step(
        self,
        request: LeaseOptionSequenceStepRequest,
    ) -> dict[str, str]:
        lead = self.contacts.get_lead(request.lead_id)
        if lead is None:
            return {"message_id": f"msg_{request.lead_id}_{request.day}_{request.channel}", "channel": request.channel, "status": "queued"}
        if request.channel == "sms":
            if not (
                self.settings.textgrid_account_sid
                and self.settings.textgrid_auth_token
                and self.settings.textgrid_from_number
            ):
                return {"message_id": f"msg_{request.lead_id}_{request.day}_sms", "channel": request.channel, "status": "queued"}
            message_body = f"Day {request.day + 1}: lease-option follow-up"
            outbound_request = build_outbound_sms_request(
                account_sid=self.settings.textgrid_account_sid,
                auth_token=self.settings.textgrid_auth_token,
                from_number=self.settings.textgrid_from_number,
                to_number=lead.phone,
                body=message_body,
                base_url=self.settings.textgrid_sms_url or "https://api.textgrid.com",
            )
            self.request_sender(outbound_request)
            self.message_logging_hook.log_sequence_dispatch(
                lead_id=lead.id,
                channel="sms",
                body=message_body,
                provider="textgrid",
            )
        elif request.channel == "email" and lead.email and self.settings.resend_api_key and self.settings.resend_from_email:
            message_body = f"Hi {lead.first_name}, just checking in on your lease-option request."
            self.request_sender(
                build_send_email_request(
                    api_key=self.settings.resend_api_key,
                    from_email=self.settings.resend_from_email,
                    to_email=lead.email,
                    subject="Checking in on your lease-option request",
                    text_body=message_body,
                )
            )
            self.message_logging_hook.log_sequence_dispatch(
                lead_id=lead.id,
                channel="email",
                body=message_body,
                provider="resend",
            )
        else:
            return {"message_id": f"msg_{request.lead_id}_{request.day}_{request.channel}", "channel": request.channel, "status": "queued"}
        return {"message_id": f"msg_{request.lead_id}_{request.day}_{request.channel}", "channel": request.channel, "status": "queued"}

    @staticmethod
    def _decide_action(event: NormalizedSmsEvent) -> SmsAction:
        if event.event_type != "inbound":
            return "ignore"
        body = event.body.strip().lower()
        if body in {"stop", "unsubscribe", "opt out"}:
            return "stop"
        if "call me" in body or "agent" in body:
            return "pause"
        return "qualify"


def _default_request_sender(outbound_request: dict[str, Any]) -> None:
    headers = {
        str(key): str(value)
        for key, value in dict(outbound_request.get("headers") or {}).items()
    }
    payload = outbound_request.get("payload")
    content_type = headers.get("Content-Type", "")
    if payload is None:
        body = None
    elif content_type == "application/x-www-form-urlencoded":
        body = urlencode(payload).encode("utf-8")
    else:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        str(outbound_request["endpoint"]),
        data=body,
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=10):
        return None


inbound_sms_service = InboundSmsService()
