from __future__ import annotations

import re
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings


ProviderComplete = Callable[[dict[str, Any]], str | None]

STOP_TERMS = {"stop", "unsubscribe", "cancel", "remove me", "do not text", "dont text"}
WRONG_NUMBER_TERMS = {"wrong number", "wrong person", "not me"}
LEGAL_TERMS = {"attorney", "lawyer", "court", "sue", "probate court", "lawsuit", "legal advice", "tax advice"}
ANGRY_TERMS = {"scam", "fraud", "harass", "harassment", "leave me alone", "reported"}
INTEREST_TERMS = {"yes", "interested", "call me", "tell me more", "offer", "how much", "cash"}
APPOINTMENT_TERMS = {"schedule", "appointment", "meet", "call tomorrow", "call today", "call me tomorrow"}
QUESTION_STARTERS = ("what", "how", "why", "when", "where", "who", "can", "could", "would", "do", "does", "is", "are")
URGENT_TERMS = {"asap", "urgent", "today", "now"}

AUTO_ACK_INTENTS = {"interested", "question", "appointment_request", "unknown"}


class SmsReplyContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    message_id: str | None = None
    contact_id: str | None = None
    from_number: str = Field(min_length=1)
    to_number: str = Field(min_length=1)
    body: str = Field(min_length=1)
    resolved: bool
    ambiguous: bool
    sms_consent: bool
    suppressed: bool
    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    lead_context: dict[str, Any] = Field(default_factory=dict)


class SmsReplyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    intent: str = Field(min_length=1)
    source_lane: str = Field(min_length=1)
    temperature: str = Field(min_length=1)
    urgency: str = Field(min_length=1)
    action: str = Field(min_length=1)
    suggested_body: str | None = None
    confidence: float = Field(ge=0, le=1)
    policy_reason: str = Field(min_length=1)
    suppress_contact: bool = False
    handoff_required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SmsReplyAgentService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        provider_complete: ProviderComplete | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.provider_complete = provider_complete

    def decide(self, context: SmsReplyContext) -> SmsReplyDecision:
        normalized_body = _normalize_text(context.body)
        intent = _classify_intent(normalized_body)
        source_lane = _source_lane(context, normalized_body)
        urgency = _urgency(intent, normalized_body)
        suppress_contact = intent == "stop"
        action, policy_reason, handoff_required = self._policy(context=context, intent=intent, urgency=urgency)

        return SmsReplyDecision(
            intent=intent,
            source_lane=source_lane,
            temperature=_temperature(intent=intent, action=action, urgency=urgency),
            urgency=urgency,
            action=action,
            suggested_body=_suggested_body(intent, source_lane) if action in {"draft_only", "auto_ack"} else None,
            confidence=_confidence(intent, context),
            policy_reason=policy_reason,
            suppress_contact=suppress_contact,
            handoff_required=handoff_required,
            metadata={
                "job_id": context.job_id,
                "message_id": context.message_id,
                "contact_id": context.contact_id,
                "provider_completion_used": False,
            },
        )

    def _policy(self, *, context: SmsReplyContext, intent: str, urgency: str) -> tuple[str, str, bool]:
        if intent == "stop":
            return "human_handoff", "Stop request", True
        if intent == "wrong_number":
            return "human_handoff", "Wrong-number reply", True
        if intent == "legal_sensitive":
            return "human_handoff", "Legal-sensitive reply", True
        if context.ambiguous or not context.resolved:
            return "human_handoff", "Ambiguous or unresolved sender", True
        if context.suppressed:
            return "human_handoff", "Contact is suppressed", True
        if not context.sms_consent:
            return "human_handoff", "Missing SMS consent", True
        if urgency == "urgent":
            return "human_handoff", "Urgent reply requires human handoff", True
        if self.settings.sms_agent_mode == "record_only":
            return "record_only", "SMS agent is in record-only mode", False
        if (
            self.settings.provider_live_sends_enabled
            and self.settings.sms_agent_auto_replies_enabled
            and self.settings.sms_agent_mode == "auto_ack"
            and intent in AUTO_ACK_INTENTS
        ):
            return "auto_ack", "Auto acknowledgement allowed by policy gates", False
        return "draft_only", "Draft-only mode or live reply gates disabled", False


def _normalize_text(body: str) -> str:
    return re.sub(r"\s+", " ", body.casefold()).strip()


def _classify_intent(body: str) -> str:
    if _has_term(body, STOP_TERMS):
        return "stop"
    if _has_term(body, WRONG_NUMBER_TERMS):
        return "wrong_number"
    if _has_term(body, LEGAL_TERMS | ANGRY_TERMS):
        return "legal_sensitive"
    if _has_term(body, APPOINTMENT_TERMS):
        return "appointment_request"
    if _has_term(body, INTEREST_TERMS):
        return "interested"
    if "?" in body or body.startswith(QUESTION_STARTERS):
        return "question"
    return "unknown"


def _has_term(body: str, terms: set[str]) -> bool:
    return any(_contains_term(body, term) for term in terms)


def _contains_term(body: str, term: str) -> bool:
    if " " in term:
        return term in body
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", body) is not None


def _source_lane(context: SmsReplyContext, body: str) -> str:
    source_lane = context.lead_context.get("source_lane")
    if isinstance(source_lane, str) and source_lane.strip():
        return source_lane.strip()
    lead_lane = context.lead_context.get("lane")
    if isinstance(lead_lane, str) and lead_lane.strip():
        return _normalize_lane(lead_lane)
    if _has_term(body, {"probate", "estate", "heir", "inherited", "executor", "administrator"}):
        return "outbound_probate"
    if _has_term(body, {"lease option", "rent to own", "seller finance", "creative finance", "booking"}):
        return "inbound_lease_option"
    return "unknown"


def _normalize_lane(value: str) -> str:
    normalized = value.casefold().replace("-", "_").replace(" ", "_")
    if "probate" in normalized:
        return "outbound_probate"
    if "lease" in normalized or "rent_to_own" in normalized:
        return "inbound_lease_option"
    return normalized or "unknown"


def _urgency(intent: str, body: str) -> str:
    if intent in {"stop", "wrong_number", "legal_sensitive"}:
        return "urgent"
    if _has_term(body, URGENT_TERMS):
        return "urgent"
    if intent == "appointment_request":
        return "normal"
    return "low"


def _temperature(*, intent: str, action: str, urgency: str) -> str:
    if action == "human_handoff" or urgency == "urgent":
        return "hot"
    if intent in {"interested", "appointment_request"}:
        return "warm"
    return "cold"


def _confidence(intent: str, context: SmsReplyContext) -> float:
    if context.ambiguous or not context.resolved:
        return 0.35
    if intent in {"stop", "wrong_number", "legal_sensitive"}:
        return 0.95
    if intent in {"interested", "appointment_request", "question"}:
        return 0.8
    return 0.55


def _suggested_body(intent: str, source_lane: str) -> str:
    if intent == "appointment_request":
        return "Thanks for reaching out. I can help coordinate a time for a quick call."
    if intent == "question":
        return "Thanks for the question. I can have someone review this and follow up with the right details."
    if intent == "interested" and source_lane == "outbound_probate":
        return "Thanks for replying. I can have someone follow up about the property and next steps."
    if intent == "interested" and source_lane == "inbound_lease_option":
        return "Thanks for replying. I can have someone follow up about the lease-option details."
    return "Thanks for replying. I can have someone follow up with more details."
