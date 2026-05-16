from app.core.config import Settings
from app.services.sms_reply_agent_service import SmsReplyAgentService, SmsReplyContext


def _context(**overrides) -> SmsReplyContext:
    values = {
        "business_id": "limitless",
        "environment": "dev",
        "job_id": "smsjob_1",
        "message_id": "msg_1",
        "contact_id": "lead_1",
        "from_number": "+15551234567",
        "to_number": "+13467725914",
        "body": "yes",
        "resolved": True,
        "ambiguous": False,
        "sms_consent": True,
        "suppressed": False,
        "recent_messages": [],
        "lead_context": {},
    }
    values.update(overrides)
    return SmsReplyContext(**values)


def _auto_ack_service() -> SmsReplyAgentService:
    return SmsReplyAgentService(
        settings=Settings(
            _env_file=None,
            sms_agent_mode="auto_ack",
            sms_agent_auto_replies_enabled=True,
            provider_live_sends_enabled=True,
        )
    )


def test_sms_reply_agent_stop_is_terminal_without_provider_call() -> None:
    calls = []
    service = SmsReplyAgentService(settings=Settings(_env_file=None), provider_complete=lambda request: calls.append(request))

    decision = service.decide(_context(body="stop texting me"))

    assert decision.intent == "stop"
    assert decision.action == "human_handoff"
    assert decision.suppress_contact is True
    assert decision.handoff_required is True
    assert calls == []


def test_sms_reply_agent_ambiguous_match_blocks_auto_send() -> None:
    calls = []
    service = SmsReplyAgentService(
        settings=Settings(
            _env_file=None,
            sms_agent_mode="auto_ack",
            sms_agent_auto_replies_enabled=True,
            provider_live_sends_enabled=True,
        ),
        provider_complete=lambda request: calls.append(request),
    )

    decision = service.decide(
        _context(
            contact_id=None,
            body="yes",
            resolved=False,
            ambiguous=True,
            sms_consent=False,
        )
    )

    assert decision.action == "human_handoff"
    assert decision.policy_reason == "Ambiguous or unresolved sender"
    assert decision.handoff_required is True
    assert calls == []


def test_sms_reply_agent_defaults_to_draft_only_for_interested_reply() -> None:
    service = SmsReplyAgentService(settings=Settings(_env_file=None))

    decision = service.decide(
        _context(
            body="Yes I am interested",
            lead_context={"source_lane": "outbound_probate"},
        )
    )

    assert decision.intent == "interested"
    assert decision.source_lane == "outbound_probate"
    assert decision.action == "draft_only"
    assert decision.suggested_body


def test_sms_reply_agent_record_only_mode_blocks_draft_and_send() -> None:
    service = SmsReplyAgentService(settings=Settings(_env_file=None, sms_agent_mode="record_only"))

    decision = service.decide(_context(body="Can you call me tomorrow?"))

    assert decision.intent == "appointment_request"
    assert decision.action == "record_only"
    assert decision.handoff_required is False


def test_sms_reply_agent_auto_ack_requires_all_live_reply_gates() -> None:
    calls = []
    service = SmsReplyAgentService(
        settings=Settings(
            _env_file=None,
            sms_agent_mode="auto_ack",
            sms_agent_auto_replies_enabled=True,
            provider_live_sends_enabled=True,
        ),
        provider_complete=lambda request: calls.append(request),
    )

    decision = service.decide(
        _context(
            body="yes tell me more",
            lead_context={"source_lane": "inbound_lease_option"},
        )
    )

    assert decision.intent == "interested"
    assert decision.source_lane == "inbound_lease_option"
    assert decision.action == "auto_ack"
    assert calls == []


def test_sms_reply_agent_urgent_reply_blocks_auto_ack() -> None:
    service = _auto_ack_service()

    decision = service.decide(_context(body="urgent can you call me today"))

    assert decision.urgency == "urgent"
    assert decision.action == "human_handoff"
    assert decision.policy_reason == "Urgent reply requires human handoff"
    assert decision.handoff_required is True


def test_sms_reply_agent_nonurgent_appointment_can_auto_ack() -> None:
    service = _auto_ack_service()

    decision = service.decide(_context(body="can you call me tomorrow"))

    assert decision.intent == "appointment_request"
    assert decision.urgency == "normal"
    assert decision.action == "auto_ack"


def test_sms_reply_agent_wrong_number_blocks_auto_ack() -> None:
    service = _auto_ack_service()

    decision = service.decide(_context(body="wrong number"))

    assert decision.intent == "wrong_number"
    assert decision.action == "human_handoff"
    assert decision.handoff_required is True


def test_sms_reply_agent_legal_or_angry_reply_blocks_auto_ack() -> None:
    service = _auto_ack_service()

    legal_decision = service.decide(_context(body="my attorney will call you"))
    angry_decision = service.decide(_context(body="this is a scam leave me alone"))

    assert legal_decision.intent == "legal_sensitive"
    assert legal_decision.action == "human_handoff"
    assert angry_decision.intent == "legal_sensitive"
    assert angry_decision.action == "human_handoff"


def test_sms_reply_agent_suppressed_contact_blocks_auto_ack() -> None:
    service = _auto_ack_service()

    decision = service.decide(_context(body="yes", suppressed=True))

    assert decision.action == "human_handoff"
    assert decision.policy_reason == "Contact is suppressed"
    assert decision.handoff_required is True


def test_sms_reply_agent_missing_sms_consent_blocks_auto_ack() -> None:
    service = _auto_ack_service()

    decision = service.decide(_context(body="yes", sms_consent=False))

    assert decision.action == "human_handoff"
    assert decision.policy_reason == "Missing SMS consent"
    assert decision.handoff_required is True
