from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import httpx

from app.core.config import Settings, get_settings
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.sms_agent import SmsAgentRepository
from app.models.sms_agent import (
    SmsAgentApproveSendRequest,
    SmsAgentEvalLabelRecord,
    SmsAgentEvalLabelRequest,
    SmsAgentJobCreate,
    SmsAgentJobRecord,
    SmsAgentReplyDecisionCreate,
    SmsAgentReplyDecisionRecord,
    SmsAgentSendRequest,
    SmsAgentSendResponse,
)
from app.providers.textgrid import build_outbound_sms_request, normalize_phone_number
from app.services.sms_reply_agent_service import SmsReplyAgentService, SmsReplyContext

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
        contacts: ContactsRepository | None = None,
        messages: MessagesRepository | None = None,
        sms_agent_repository: SmsAgentRepository | None = None,
        request_sender: RequestSender | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.conversations = conversations or ConversationsRepository(settings=self.settings)
        self.contacts = contacts or ContactsRepository(settings=self.settings)
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
                    "body": event.body,
                    "body_preview": event.body[:160],
                    "sms_consent": lead.sms_consent,
                    "resolved": True,
                    "lead_context": {
                        key: value
                        for key, value in {
                            "property_address": lead.property_address,
                            "property_type": lead.property_type,
                            "timeline_to_sell": lead.timeline_to_sell,
                            "seller_goal": lead.seller_goal,
                            "source_lane": lead.utm_campaign or lead.utm_source,
                        }.items()
                        if value not in (None, "")
                    },
                },
            )
        )
        return job.id

    def record_eval_label(
        self,
        decision_id: str,
        request: SmsAgentEvalLabelRequest,
    ) -> SmsAgentEvalLabelRecord:
        return self.sms_agent_repository.record_eval_label(decision_id, request)

    def approve_send(
        self,
        decision_id: str,
        request: SmsAgentApproveSendRequest,
    ) -> SmsAgentSendResponse:
        if request.operator_approval is not True:
            raise ValueError("operator_approval is required")
        decision = self.sms_agent_repository.get_decision(decision_id)
        if decision is None:
            raise ValueError("SMS agent decision does not exist")
        if decision.action != "draft_only":
            raise ValueError("Only draft_only SMS agent decisions can be approved")
        job = self.sms_agent_repository.get_job(decision.job_id)
        if job is None:
            raise ValueError("SMS agent job does not exist")
        if not decision.contact_id or not decision.contact_id.startswith("ctc_"):
            raise ValueError("resolved contact is required")
        body = request.edited_body or decision.suggested_body
        if not body or not body.strip():
            raise ValueError("SMS body is required")
        contact = self.contacts.get_lead(decision.contact_id)
        if contact is None:
            raise ValueError("resolved contact is required")
        contact_phone = normalize_phone_number(contact.phone)
        reply_phone = normalize_phone_number(job.from_number)
        if (
            contact.business_id != decision.business_id
            or contact.environment != decision.environment
            or contact_phone != reply_phone
        ):
            raise ValueError("resolved contact is required")
        if contact.sms_consent is not True:
            raise ValueError("SMS consent is required")
        sent_body = body.strip()
        send_request = SmsAgentSendRequest(
            business_id=decision.business_id,
            environment=decision.environment,
            contact_id=decision.contact_id,
            conversation_id=decision.conversation_id or job.conversation_id,
            to=job.from_number,
            body=sent_body,
            sms_consent_confirmed=True,
            dry_run_only=False,
            metadata={
                "sms_agent_job_id": job.id,
                "sms_agent_decision_id": decision.id,
                "operator_approval": True,
            },
        )

        follow_ups = self._operator_send_follow_ups(decision)
        existing_response = self._stored_operator_send_response(follow_ups)
        if existing_response is not None:
            return existing_response

        self._preflight_live_send(send_request)
        self._record_operator_send_follow_up(
            decision=decision,
            job=job,
            action="operator_send_requested",
            sent_body=sent_body,
            policy_reason="Operator send requested",
            metadata={"operator_approval": True},
        )

        try:
            response = self.send_message(send_request)
        except Exception as exc:
            self._record_operator_send_follow_up(
                decision=decision,
                job=job,
                action="operator_send_failed",
                sent_body=sent_body,
                policy_reason="Operator approved send failed",
                metadata={
                    "operator_approval": True,
                    "error_message": str(exc),
                },
            )
            raise

        self._record_operator_send_follow_up(
            decision=decision,
            job=job,
            action="operator_approved_send",
            sent_body=sent_body,
            policy_reason="Operator approved send",
            conversation_id=response.conversation_id or decision.conversation_id or job.conversation_id,
            metadata={
                "operator_approval": True,
                "response": response.model_dump(mode="json"),
            },
        )
        return response

    def _preflight_live_send(self, request: SmsAgentSendRequest) -> None:
        if request.dry_run_only or not self.settings.provider_live_sends_enabled:
            return
        self._require_textgrid_config()
        if not request.contact_id:
            raise RuntimeError("contact_id is required for live SMS sends")
        if not request.sms_consent_confirmed:
            raise RuntimeError("sms_consent_confirmed is required for live SMS sends")
        provider_thread_id = request.conversation_id or normalize_phone_number(request.to)
        self.conversations.get_or_create(
            business_id=request.business_id,
            environment=request.environment,
            contact_id=request.contact_id,
            channel="sms",
            provider_thread_id=provider_thread_id,
        )

    def _operator_send_follow_ups(
        self,
        decision: SmsAgentReplyDecisionRecord,
    ) -> list[SmsAgentReplyDecisionRecord]:
        decisions = self.sms_agent_repository.list_decisions(
            business_id=decision.business_id,
            environment=decision.environment,
        )
        return [
            follow_up
            for follow_up in decisions
            if follow_up.job_id == decision.job_id and follow_up.metadata.get("parent_decision_id") == decision.id
        ]

    @staticmethod
    def _stored_operator_send_response(
        follow_ups: list[SmsAgentReplyDecisionRecord],
    ) -> SmsAgentSendResponse | None:
        for follow_up in reversed(follow_ups):
            if follow_up.action != "operator_approved_send":
                continue
            response = follow_up.metadata.get("response")
            if isinstance(response, dict):
                return SmsAgentSendResponse.model_validate(response)
        return None

    def _record_operator_send_follow_up(
        self,
        *,
        decision: SmsAgentReplyDecisionRecord,
        job: SmsAgentJobRecord,
        action: str,
        sent_body: str,
        policy_reason: str,
        metadata: dict[str, Any],
        conversation_id: str | None = None,
    ) -> SmsAgentReplyDecisionRecord:
        create = SmsAgentReplyDecisionCreate(
            business_id=decision.business_id,
            environment=decision.environment,
            job_id=job.id,
            message_id=decision.message_id or job.message_id,
            conversation_id=conversation_id or decision.conversation_id or job.conversation_id,
            contact_id=decision.contact_id,
            intent=decision.intent,
            source_lane=decision.source_lane,
            temperature=decision.temperature,
            urgency=decision.urgency,
            action=action,
            suggested_body=sent_body,
            confidence=decision.confidence,
            policy_reason=policy_reason,
            prompt_version=decision.prompt_version,
            provider_kind="operator",
            metadata={
                "parent_decision_id": decision.id,
                "sent_body": sent_body,
                **metadata,
            },
        )
        if action == "operator_send_requested":
            return self.sms_agent_repository.record_operator_send_request(create)
        return self.sms_agent_repository.record_decision(create)

    def process_pending(self, limit: int | None = None) -> dict[str, int]:
        batch_limit = limit or self.settings.sms_agent_process_batch_size
        jobs = self.sms_agent_repository.claim_pending(batch_limit, self.settings.sms_agent_lock_seconds)
        result = {
            "processed_count": len(jobs),
            "sent_count": 0,
            "blocked_count": 0,
            "failed_count": 0,
        }
        reply_agent = SmsReplyAgentService(settings=self.settings)
        for job in jobs:
            recorded_decision_id: str | None = None
            try:
                context = self._reply_context_for_job(job)
                decision = reply_agent.decide(context)
                recorded = self.sms_agent_repository.record_decision(
                    SmsAgentReplyDecisionCreate(
                        business_id=job.business_id,
                        environment=job.environment,
                        job_id=job.id,
                        message_id=job.message_id,
                        conversation_id=job.conversation_id,
                        contact_id=job.contact_id,
                        intent=decision.intent,
                        source_lane=decision.source_lane,
                        temperature=decision.temperature,
                        urgency=decision.urgency,
                        action=decision.action,
                        suggested_body=decision.suggested_body,
                        confidence=decision.confidence,
                        policy_reason=decision.policy_reason,
                        prompt_version=self.settings.sms_agent_prompt_version,
                        provider_kind="deterministic",
                        metadata={
                            **decision.metadata,
                            "job_metadata": job.metadata,
                            "suppress_contact": decision.suppress_contact,
                            "handoff_required": decision.handoff_required,
                        },
                    )
                )
                recorded_decision_id = recorded.id
                if decision.action == "auto_ack":
                    response = self.send_message(
                        SmsAgentSendRequest(
                            business_id=job.business_id,
                            environment=job.environment,
                            contact_id=job.contact_id,
                            conversation_id=job.conversation_id,
                            to=job.from_number,
                            body=decision.suggested_body or "Thanks for replying. We will follow up.",
                            sms_consent_confirmed=True,
                            dry_run_only=False,
                            metadata={
                                "sms_agent_job_id": job.id,
                                "sms_agent_decision_id": recorded.id,
                            },
                        )
                    )
                    if not response.dry_run and response.status != "failed" and response.error_message is None:
                        result["sent_count"] += 1
                elif decision.action == "human_handoff":
                    result["blocked_count"] += 1
                self.sms_agent_repository.mark_completed(job.id, decision_id=recorded.id)
            except Exception as exc:
                retryable = job.attempt_count < self.settings.sms_agent_max_attempts
                self.sms_agent_repository.mark_failed(
                    job.id,
                    retryable=retryable,
                    error_message=str(exc),
                    decision_id=recorded_decision_id,
                )
                result["failed_count"] += 1
        return result

    def _reply_context_for_job(self, job: SmsAgentJobRecord) -> SmsReplyContext:
        metadata = job.metadata
        body_value = metadata.get("body") or metadata.get("body_preview") or ""
        message = self.messages.get(job.message_id)
        if message is not None and message.body.strip():
            body_value = message.body
        body = str(body_value).strip()
        ambiguous = _metadata_bool(metadata, "ambiguous", default=False)
        if not body:
            body = "Inbound SMS body missing"
            ambiguous = True
        resolved = bool(job.contact_id)
        if isinstance(metadata.get("resolved"), bool):
            resolved = bool(metadata["resolved"])
        lead_context = self._lead_context_for_job(job)
        existing_lead_context = metadata.get("lead_context")
        if isinstance(existing_lead_context, dict):
            lead_context.update(existing_lead_context)
        source_lane = metadata.get("source_lane")
        if isinstance(source_lane, str) and source_lane.strip():
            lead_context["source_lane"] = source_lane.strip()
        return SmsReplyContext(
            business_id=job.business_id,
            environment=job.environment,
            job_id=job.id,
            message_id=job.message_id,
            contact_id=job.contact_id,
            from_number=job.from_number,
            to_number=job.to_number,
            body=body,
            resolved=resolved,
            ambiguous=ambiguous,
            sms_consent=_metadata_bool(metadata, "sms_consent", default=False),
            suppressed=_metadata_bool(metadata, "suppressed", default=False),
            recent_messages=self._recent_messages_for_job(job),
            lead_context=lead_context,
            manual_control=_metadata_bool(metadata, "manual_control", default=False)
            or _metadata_bool(lead_context, "manual_control", default=False)
            or str(lead_context.get("conversation_owner") or "").casefold() in {"martin", "manual", "human"},
            appointment_setter_paused=_metadata_bool(metadata, "appointment_setter_paused", default=False)
            or _metadata_bool(lead_context, "appointment_setter_paused", default=False)
            or str(metadata.get("conversation_status") or lead_context.get("conversation_status") or "").casefold()
            in {"appointment_setter_paused", "manual_takeover", "manual_control", "paused"},
            conversation_status=str(metadata.get("conversation_status") or lead_context.get("conversation_status") or ""),
        )

    def _lead_context_for_job(self, job: SmsAgentJobRecord) -> dict[str, Any]:
        if not job.contact_id:
            return {}
        lead = self.contacts.get_lead(job.contact_id)
        if lead is None:
            return {}
        return {
            key: value
            for key, value in {
                "source_lane": lead.utm_campaign or lead.utm_source,
                "property_address": lead.property_address,
                "property_type": lead.property_type,
                "timeline_to_sell": lead.timeline_to_sell,
                "seller_goal": lead.seller_goal,
                "booking_status": lead.booking_status,
                "notes": lead.notes,
                "sms_consent": lead.sms_consent,
            }.items()
            if value not in (None, "")
        }

    def _recent_messages_for_job(self, job: SmsAgentJobRecord) -> list[dict[str, Any]]:
        if not job.contact_id:
            return []
        try:
            messages = self.messages.list_recent_for_contact(
                business_id=job.business_id,
                environment=job.environment,
                contact_id=job.contact_id,
                channel="sms",
                limit=8,
            )
        except Exception:  # noqa: BLE001
            return []
        return [
            {
                "id": message.id,
                "direction": str(message.direction.value if hasattr(message.direction, "value") else message.direction),
                "status": str(message.status.value if hasattr(message.status, "value") else message.status),
                "body": message.body[:320],
                "created_at": message.created_at.isoformat() if hasattr(message.created_at, "isoformat") else str(message.created_at),
            }
            for message in messages
        ]

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


def _metadata_bool(metadata: dict[str, Any], key: str, *, default: bool) -> bool:
    value = metadata.get(key)
    return value if isinstance(value, bool) else default
