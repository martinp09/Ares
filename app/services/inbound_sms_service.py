from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Literal, Protocol
from urllib import request
from urllib.parse import urlencode

from app.core.config import Settings, get_settings
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.lead_events import LeadEventsRepository
from app.db.lead_machine_supabase import lead_machine_backend_enabled
from app.db.messages import MessagesRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.sequences import SequencesRepository
from app.db.tasks import TasksRepository
from app.models.lead_events import LeadEventRecord, ProviderWebhookReceiptRecord
from app.models.marketing_leads import MarketingLeadRecord
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType
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


@dataclass(slots=True)
class ResolvedInboundLead:
    lead: MarketingLeadRecord | None
    provider_thread_id: str | None
    thread_matched: bool = False
    ambiguous: bool = False
    unresolved: bool = False


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
    def append_inbound_message(
        self,
        event: NormalizedSmsEvent,
        *,
        lead: MarketingLeadRecord,
        provider_thread_id: str | None = None,
    ) -> None: ...


class SequenceReplyService(Protocol):
    def stop(
        self,
        *,
        phone_number: str,
        business_id: str | None = None,
        environment: str | None = None,
        contact_id: str | None = None,
    ) -> None: ...

    def pause(
        self,
        *,
        phone_number: str,
        business_id: str | None = None,
        environment: str | None = None,
        contact_id: str | None = None,
    ) -> None: ...


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

    def append_inbound_message(
        self,
        event: NormalizedSmsEvent,
        *,
        lead: MarketingLeadRecord,
        provider_thread_id: str | None = None,
    ) -> None:
        if event.event_type != "inbound":
            return
        conversation = self.conversations.get_or_create(
            business_id=lead.business_id,
            environment=lead.environment,
            contact_id=lead.id,
            channel="sms",
            provider_thread_id=provider_thread_id,
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

    def stop(
        self,
        *,
        phone_number: str,
        business_id: str | None = None,
        environment: str | None = None,
        contact_id: str | None = None,
    ) -> None:
        self._update(
            phone_number=phone_number,
            action="stop",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
        )

    def pause(
        self,
        *,
        phone_number: str,
        business_id: str | None = None,
        environment: str | None = None,
        contact_id: str | None = None,
    ) -> None:
        self._update(
            phone_number=phone_number,
            action="pause",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
        )

    def _update(
        self,
        *,
        phone_number: str,
        action: Literal["pause", "stop"],
        business_id: str | None = None,
        environment: str | None = None,
        contact_id: str | None = None,
    ) -> None:
        resolved_business_id = business_id
        resolved_environment = environment
        resolved_contact_id = contact_id
        if not (resolved_business_id and resolved_environment and resolved_contact_id):
            lead = self.contacts.find_by_phone(
                phone=phone_number,
                business_id=business_id,
                environment=environment,
            )
            if lead is None:
                return
            resolved_business_id = lead.business_id
            resolved_environment = lead.environment
            resolved_contact_id = lead.id
        enrollment = self.sequences.find_active(
            business_id=resolved_business_id,
            environment=resolved_environment,
            contact_id=resolved_contact_id,
            sequence_key=LEASE_OPTION_SEQUENCE_KEY,
        )
        if enrollment is None:
            return
        if action == "pause":
            self.sequences.pause(
                enrollment.id,
                business_id=resolved_business_id,
                environment=resolved_environment,
            )
        else:
            self.sequences.stop(
                enrollment.id,
                business_id=resolved_business_id,
                environment=resolved_environment,
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
        metadata = dict(event.metadata or {})
        business_id = lead.business_id if lead is not None else str(metadata.get("business_id") or "unknown")
        environment = lead.environment if lead is not None else str(metadata.get("environment") or "unknown")
        idempotency_seed = event.external_id or (
            f"{event.event_type}:{event.from_number}:{event.to_number}:{event.body.strip().casefold()}"
        )
        receipt = self.provider_webhooks.record(
            ProviderWebhookReceiptRecord(
                business_id=business_id,
                environment=environment,
                provider="textgrid",
                event_type=event.event_type,
                idempotency_key=f"textgrid:{idempotency_seed}",
                provider_event_id=event.external_id,
                provider_receipt_id=event.external_id,
                lead_email=lead.email if lead is not None else None,
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
        self.conversations = conversations or ConversationsRepository(self.contacts.client)
        self.messages = messages or MessagesRepository(self.contacts.client)

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
        conversations: ConversationsRepository | None = None,
        webhook_receipts: WebhookReceiptService | None = None,
        message_logging_hook: MessageLoggingHook | None = None,
        lead_events_repository: LeadEventsRepository | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.textgrid_adapter = textgrid_adapter or _DefaultTextgridWebhookAdapter(self.settings)
        self.contacts = contacts or ContactsRepository()
        repo_force_memory = getattr(self.contacts, "_force_memory", False)
        self.conversations = conversations or ConversationsRepository(
            self.contacts.client,
            settings=self.settings,
            force_memory=repo_force_memory,
        )
        self.message_repository = message_repository or _MarketingMessageRepository(
            contacts=self.contacts,
            conversations=self.conversations,
            messages=MessagesRepository(
                self.contacts.client,
                settings=self.settings,
                force_memory=repo_force_memory,
            ),
        )
        self.sequence_service = sequence_service or _SequenceReplyAdapter(
            contacts=self.contacts,
            sequences=SequencesRepository(
                self.contacts.client,
                settings=self.settings,
                force_memory=repo_force_memory,
            ),
        )
        self.request_sender = request_sender or _default_request_sender
        self.tasks = TasksRepository(
            self.contacts.client,
            settings=self.settings,
            force_memory=repo_force_memory,
        )
        self.webhook_receipts = webhook_receipts or _ProviderWebhookReceiptAdapter(
            ProviderWebhooksRepository(
                self.contacts.client,
                settings=self.settings,
                force_memory=repo_force_memory,
            )
        )
        self.message_logging_hook = message_logging_hook or _RepositoryMessageLoggingHook(
            contacts=self.contacts,
            conversations=self.conversations,
            messages=MessagesRepository(
                self.contacts.client,
                settings=self.settings,
                force_memory=repo_force_memory,
            ),
        )
        self.lead_events_repository = lead_events_repository or LeadEventsRepository(self.contacts.client, settings=self.settings)

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
        resolved = self._resolve_inbound_lead(event)
        should_record_receipt = (
            not lead_machine_backend_enabled(self.settings)
            or resolved.lead is not None
            or self._has_tenant_metadata(event)
        )
        receipt_id: str | None = None
        deduped = False
        if should_record_receipt:
            receipt_id, deduped = self.webhook_receipts.record_textgrid_event(event=event, lead=resolved.lead, payload=payload)
            if deduped:
                self.webhook_receipts.mark_processed(receipt_id)
                return {"status": "processed", "event_type": event.event_type, "action": self._decide_action(event)}
        if resolved.lead is not None:
            self._append_inbound_message(
                event=event,
                lead=resolved.lead,
                provider_thread_id=resolved.provider_thread_id if resolved.thread_matched else None,
            )
        if resolved.ambiguous or resolved.unresolved:
            self._record_inbound_review_signal(event=event, resolved=resolved)
            self._create_inbound_manual_review_task(event, resolved=resolved)
        action = self._decide_action(event)
        if resolved.lead is not None:
            if action == "stop":
                self._mutate_sequence(action=action, lead=resolved.lead)
            elif action == "pause":
                self._mutate_sequence(action=action, lead=resolved.lead)
        if receipt_id is not None:
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

    def _resolve_inbound_lead(self, event: NormalizedSmsEvent) -> ResolvedInboundLead:
        metadata = dict(event.metadata or {})
        provider_thread_id = self._extract_provider_thread_id(metadata)
        business_id = metadata.get("business_id")
        environment = metadata.get("environment")
        tenant_business = str(business_id) if business_id else None
        tenant_environment = str(environment) if environment else None
        if provider_thread_id and tenant_business and tenant_environment:
            conversation = self.conversations.find_by_provider_thread(
                business_id=tenant_business,
                environment=tenant_environment,
                channel="sms",
                provider_thread_id=provider_thread_id,
            )
            if conversation is not None:
                lead = self.contacts.get_lead(conversation.contact_id)
                if lead is not None:
                    return ResolvedInboundLead(lead=lead, provider_thread_id=provider_thread_id, thread_matched=True)

        tenant_business = str(business_id) if business_id else None
        tenant_environment = str(environment) if environment else None
        phone_matches = self.contacts.find_all_by_phone(
            phone=event.from_number,
            business_id=tenant_business,
            environment=tenant_environment,
        )
        if len(phone_matches) == 1:
            return ResolvedInboundLead(lead=phone_matches[0], provider_thread_id=provider_thread_id)
        if len(phone_matches) > 1:
            return ResolvedInboundLead(lead=None, provider_thread_id=provider_thread_id, ambiguous=True)
        return ResolvedInboundLead(lead=None, provider_thread_id=provider_thread_id, unresolved=True)

    def _append_inbound_message(
        self,
        *,
        event: NormalizedSmsEvent,
        lead: MarketingLeadRecord,
        provider_thread_id: str | None,
    ) -> None:
        try:
            self.message_repository.append_inbound_message(
                event,
                lead=lead,
                provider_thread_id=provider_thread_id,
            )
        except TypeError:
            self.message_repository.append_inbound_message(event)

    def _mutate_sequence(self, *, action: Literal["pause", "stop"], lead: MarketingLeadRecord) -> None:
        kwargs = {
            "phone_number": lead.phone,
            "business_id": lead.business_id,
            "environment": lead.environment,
            "contact_id": lead.id,
        }
        try:
            if action == "pause":
                self.sequence_service.pause(**kwargs)
            else:
                self.sequence_service.stop(**kwargs)
        except TypeError:
            if action == "pause":
                self.sequence_service.pause(phone_number=lead.phone)
            else:
                self.sequence_service.stop(phone_number=lead.phone)

    def _record_inbound_review_signal(
        self,
        *,
        event: NormalizedSmsEvent,
        resolved: ResolvedInboundLead,
    ) -> None:
        if resolved.lead is None or not lead_machine_backend_enabled(self.settings):
            return
        reason = "ambiguous_match" if resolved.ambiguous else "unmatched_inbound"
        idempotency_tail = event.external_id or f"{event.event_type}:{event.from_number}:{event.to_number}:{event.body.strip().casefold()}"
        self.lead_events_repository.append(
            LeadEventRecord(
                business_id=resolved.lead.business_id,
                environment=resolved.lead.environment,
                lead_id=resolved.lead.id,
                provider_name="textgrid",
                provider_event_id=event.external_id,
                event_type="lead.reply.needs_review",
                idempotency_key=f"inbound_sms_review:{reason}:{idempotency_tail}",
                payload={
                    "from_number": event.from_number,
                    "to_number": event.to_number,
                    "body": event.body,
                    "provider_thread_id": resolved.provider_thread_id,
                },
                metadata={
                    "reason": reason,
                    "reply_needs_review": True,
                    "thread_matched": resolved.thread_matched,
                    "ambiguous": resolved.ambiguous,
                    "unresolved": resolved.unresolved,
                },
            )
        )

    def _create_inbound_manual_review_task(
        self,
        event: NormalizedSmsEvent,
        *,
        resolved: ResolvedInboundLead,
    ) -> None:
        if lead_machine_backend_enabled(self.settings):
            return
        metadata = dict(event.metadata or {})
        business_id = str(metadata.get("business_id") or "unknown")
        environment = str(metadata.get("environment") or "unknown")
        lead_id = resolved.lead.id if resolved.lead is not None else None
        reason = "ambiguous_match" if resolved.ambiguous else "unmatched_inbound"
        idempotency_tail = event.external_id or f"{event.event_type}:{event.from_number}:{event.to_number}:{event.body.strip().casefold()}"
        dedupe_key = f"inbound_sms_review:{reason}:{idempotency_tail}"
        self.tasks.create(
            TaskRecord(
                business_id=business_id,
                environment=environment,
                title=f"Review inbound SMS ({reason})",
                status=TaskStatus.OPEN,
                task_type=TaskType.MANUAL_REVIEW,
                priority=TaskPriority.HIGH,
                lead_id=lead_id,
                details={
                    "from_number": event.from_number,
                    "to_number": event.to_number,
                    "body": event.body,
                    "provider_thread_id": resolved.provider_thread_id,
                },
                idempotency_key=dedupe_key,
            ),
            dedupe_key=dedupe_key,
        )

    @staticmethod
    def _extract_provider_thread_id(metadata: dict[str, Any]) -> str | None:
        for key in ("provider_thread_id", "thread_id", "conversation_id"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _has_tenant_metadata(event: NormalizedSmsEvent) -> bool:
        metadata = dict(event.metadata or {})
        return bool(metadata.get("business_id")) and bool(metadata.get("environment"))

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
