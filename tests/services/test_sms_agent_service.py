from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.contacts import ContactsRepository
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.sms_agent import SmsAgentRepository, SmsAgentSendRequestConflict
from app.models.marketing_leads import LeadUpsertRequest
from app.models.sms_agent import (
    SmsAgentApproveSendRequest,
    SmsAgentJobCreate,
    SmsAgentReplyDecisionCreate,
    SmsAgentSendRequest,
)
from app.services.inbound_sms_service import NormalizedSmsEvent
from app.services.sms_agent_service import SmsAgentService


def _service(settings: Settings, sent_requests: list[dict] | None = None) -> SmsAgentService:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return SmsAgentService(
        settings=settings,
        conversations=ConversationsRepository(client=client, settings=settings),
        messages=MessagesRepository(client=client, settings=settings),
        request_sender=(sent_requests or []).append,
    )


def _live_settings() -> Settings:
    return Settings(
        _env_file=None,
        provider_live_sends_enabled=True,
        textgrid_account_sid="acct_123",
        textgrid_auth_token="token_123",
        textgrid_from_number="3467725914",
    )


def _service_with_repository(
    *,
    settings: Settings | None = None,
    request_sender=None,
) -> tuple[SmsAgentService, SmsAgentRepository, ContactsRepository]:
    resolved_settings = settings or _live_settings()
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repository = SmsAgentRepository(client=client, settings=resolved_settings)
    contacts = ContactsRepository(client, settings=resolved_settings)
    service = SmsAgentService(
        settings=resolved_settings,
        conversations=ConversationsRepository(client=client, settings=resolved_settings),
        contacts=contacts,
        messages=MessagesRepository(client=client, settings=resolved_settings),
        sms_agent_repository=repository,
        request_sender=request_sender or (lambda request: {"sid": "SM123", "status": "queued"}),
    )
    return service, repository, contacts


def _persisted_contact(
    contacts: ContactsRepository,
    *,
    business_id: str = "limitless",
    environment: str = "dev",
    phone: str = "+15551234567",
    sms_consent: bool = True,
):
    return contacts.upsert_lead(
        LeadUpsertRequest(
            business_id=business_id,
            environment=environment,
            first_name="Maya",
            phone=phone,
            property_address="123 Main St, Houston, TX",
            sms_consent=sms_consent,
        )
    )


def _persisted_sms_decision(
    repository: SmsAgentRepository,
    *,
    job_metadata: dict | None = None,
    decision_metadata: dict | None = None,
    contact_id: str | None = "ctc_123",
    suggested_body: str | None = "Thanks. I will follow up shortly.",
):
    job = repository.enqueue_job(
        SmsAgentJobCreate(
            business_id="limitless",
            environment="dev",
            provider_webhook_id="wh_123",
            message_id="msg_123",
            conversation_id="cnv_123",
            contact_id=contact_id,
            from_number="+15551234567",
            to_number="+13467725914",
            metadata=job_metadata or {},
        )
    )
    decision = repository.record_decision(
        SmsAgentReplyDecisionCreate(
            business_id=job.business_id,
            environment=job.environment,
            job_id=job.id,
            message_id=job.message_id,
            conversation_id=job.conversation_id,
            contact_id=contact_id,
            intent="interested",
            source_lane="outbound_probate",
            temperature="warm",
            urgency="normal",
            action="draft_only",
            suggested_body=suggested_body,
            confidence=0.81,
            policy_reason="Operator review required",
            prompt_version="sms_reply_agent_v1",
            provider_kind="deterministic",
            metadata=decision_metadata or {},
        )
    )
    return job, decision


def test_sms_agent_dry_run_skips_provider_when_live_sends_disabled() -> None:
    sent_requests: list[dict] = []
    service = SmsAgentService(
        settings=Settings(_env_file=None, provider_live_sends_enabled=False, textgrid_from_number="3467725914"),
        request_sender=sent_requests.append,
    )

    response = service.send_message(
        SmsAgentSendRequest(
            business_id="limitless",
            environment="dev",
            to="555-123-4567",
            body="Ares dry-run SMS",
        )
    )

    assert response.dry_run is True
    assert response.status == "skipped"
    assert response.to == "+15551234567"
    assert response.log_status == "skipped_dry_run"
    assert sent_requests == []


def test_sms_agent_enqueue_inbound_reply_job_records_tenant_and_context() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    contacts = ContactsRepository(client)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )

    class RecordingRepository:
        def __init__(self) -> None:
            self.creates = []

        def enqueue_job(self, create):
            self.creates.append(create)
            return SimpleNamespace(id="smsjob_123")

    repository = RecordingRepository()
    service = SmsAgentService(
        settings=Settings(_env_file=None),
        sms_agent_repository=repository,
    )
    event = NormalizedSmsEvent(
        event_type="inbound",
        body="x" * 200,
        from_number="+15551234567",
        to_number="+13467725914",
        external_id="SM123",
        metadata={"business_id": "ignored", "environment": "ignored"},
    )

    job_id = service.enqueue_inbound_reply_job(
        event=event,
        lead=lead,
        provider_thread_id="thread_123",
        receipt_id="wh_123",
    )

    assert job_id == "smsjob_123"
    assert len(repository.creates) == 1
    create = repository.creates[0]
    assert create.business_id == lead.business_id
    assert create.environment == lead.environment
    assert create.provider_webhook_id == "wh_123"
    assert create.conversation_id == "thread_123"
    assert create.contact_id == lead.id
    assert create.from_number == "+15551234567"
    assert create.to_number == "+13467725914"
    assert create.metadata == {
        "external_id": "SM123",
        "body": "x" * 200,
        "body_preview": "x" * 160,
        "sms_consent": True,
        "resolved": True,
        "lead_context": {"property_address": "123 Main St, Houston, TX"},
    }


def test_sms_agent_enqueue_inbound_reply_job_skips_non_inbound_and_unknown_tenant() -> None:
    class FailingRepository:
        def enqueue_job(self, create):
            raise AssertionError("unknown tenant or non-inbound events should not enqueue jobs")

    service = SmsAgentService(
        settings=Settings(_env_file=None),
        sms_agent_repository=FailingRepository(),
    )

    assert (
        service.enqueue_inbound_reply_job(
            event=NormalizedSmsEvent(
                event_type="status",
                body="",
                from_number="+15551234567",
                to_number="+13467725914",
            ),
            lead=None,
            provider_thread_id=None,
            receipt_id=None,
        )
        is None
    )
    assert (
        service.enqueue_inbound_reply_job(
            event=NormalizedSmsEvent(
                event_type="inbound",
                body="Need details",
                from_number="+15551234567",
                to_number="+13467725914",
                metadata={},
            ),
            lead=None,
            provider_thread_id=None,
            receipt_id=None,
        )
        is None
    )


def test_sms_agent_enqueue_inbound_reply_job_skips_inbound_without_lead_even_with_tenant_metadata() -> None:
    class RecordingRepository:
        def __init__(self) -> None:
            self.creates = []

        def enqueue_job(self, create):
            self.creates.append(create)
            return SimpleNamespace(id="smsjob_123")

    repository = RecordingRepository()
    service = SmsAgentService(
        settings=Settings(_env_file=None),
        sms_agent_repository=repository,
    )

    job_id = service.enqueue_inbound_reply_job(
        event=NormalizedSmsEvent(
            event_type="inbound",
            body="Need details",
            from_number="+15551234567",
            to_number="+13467725914",
            external_id="SM123",
            metadata={"business_id": "limitless", "environment": "dev"},
        ),
        lead=None,
        provider_thread_id="thread_123",
        receipt_id="wh_123",
    )

    assert job_id is None
    assert repository.creates == []


def test_sms_agent_approve_send_uses_persisted_job_consent_and_records_follow_up_decision() -> None:
    sent_requests: list[dict] = []

    def fake_sender(request: dict) -> dict:
        sent_requests.append(request)
        return {"sid": "SM_APPROVED", "status": "queued"}

    service, repository, contacts = _service_with_repository(request_sender=fake_sender)
    lead = _persisted_contact(contacts)
    job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    response = service.approve_send(
        decision.id,
        SmsAgentApproveSendRequest(operator_approval=True, edited_body="Operator approved reply."),
    )

    assert response.status == "queued"
    assert response.provider_message_id == "SM_APPROVED"
    assert sent_requests[0]["payload"]["Body"] == "Operator approved reply."
    decisions = repository.list_decisions(business_id=job.business_id, environment=job.environment)
    assert [entry.action for entry in decisions] == [
        "draft_only",
        "operator_send_requested",
        "operator_approved_send",
    ]
    marker = decisions[1]
    assert marker.metadata["parent_decision_id"] == decision.id
    assert marker.metadata["operator_approval"] is True
    assert marker.suggested_body == "Operator approved reply."
    follow_up = decisions[2]
    assert follow_up.job_id == job.id
    assert follow_up.contact_id == decision.contact_id
    assert follow_up.suggested_body == "Operator approved reply."
    assert follow_up.metadata["parent_decision_id"] == decision.id
    assert follow_up.metadata["sent_body"] == "Operator approved reply."
    assert follow_up.metadata["response"]["provider_message_id"] == "SM_APPROVED"
    assert follow_up.metadata["response"]["status"] == "queued"


def test_sms_agent_approve_send_rejects_decision_metadata_consent_without_send() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {}
    )
    lead = _persisted_contact(contacts, sms_consent=False)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={},
        decision_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    with pytest.raises(ValueError, match="SMS consent is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_uses_persisted_contact_consent_without_job_metadata() -> None:
    sent_requests: list[dict] = []

    def fake_sender(request: dict) -> dict:
        sent_requests.append(request)
        return {"sid": "SM_CONTACT_CONSENT", "status": "queued"}

    service, repository, contacts = _service_with_repository(request_sender=fake_sender)
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )
    job, decision = _persisted_sms_decision(repository, job_metadata={}, contact_id=lead.id)

    response = service.approve_send(
        decision.id,
        SmsAgentApproveSendRequest(operator_approval=True, edited_body="Operator approved via contact consent."),
    )

    assert response.status == "queued"
    assert response.provider_message_id == "SM_CONTACT_CONSENT"
    assert sent_requests[0]["payload"]["Body"] == "Operator approved via contact consent."
    decisions = repository.list_decisions(business_id=job.business_id, environment=job.environment)
    assert [entry.action for entry in decisions] == [
        "draft_only",
        "operator_send_requested",
        "operator_approved_send",
    ]


def test_sms_agent_approve_send_blocks_revoked_contact_consent_even_when_job_snapshot_true() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {}
    )
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            property_address="123 Main St, Houston, TX",
            sms_consent=True,
        )
    )
    contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            property_address="123 Main St, Houston, TX",
            sms_consent=False,
        )
    )
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    with pytest.raises(ValueError, match="SMS consent is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_duplicate_returns_stored_response_without_second_provider_call() -> None:
    sent_requests: list[dict] = []

    def fake_sender(request: dict) -> dict:
        sent_requests.append(request)
        return {"sid": f"SM_APPROVED_{len(sent_requests)}", "status": "queued"}

    service, repository, contacts = _service_with_repository(request_sender=fake_sender)
    lead = _persisted_contact(contacts)
    job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    first_response = service.approve_send(
        decision.id,
        SmsAgentApproveSendRequest(operator_approval=True, edited_body="Operator approved reply."),
    )
    second_response = service.approve_send(
        decision.id,
        SmsAgentApproveSendRequest(operator_approval=True, edited_body="Operator approved reply."),
    )

    assert first_response.provider_message_id == "SM_APPROVED_1"
    assert second_response == first_response
    assert len(sent_requests) == 1
    decisions = repository.list_decisions(business_id=job.business_id, environment=job.environment)
    assert [entry.action for entry in decisions] == [
        "draft_only",
        "operator_send_requested",
        "operator_approved_send",
    ]


def test_sms_agent_approve_send_rejects_dangling_send_requested_marker_before_provider_call() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"}
    )
    lead = _persisted_contact(contacts)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )
    repository.record_decision(
        SmsAgentReplyDecisionCreate(
            business_id=decision.business_id,
            environment=decision.environment,
            job_id=decision.job_id,
            message_id=decision.message_id,
            conversation_id=decision.conversation_id,
            contact_id=decision.contact_id,
            intent=decision.intent,
            source_lane=decision.source_lane,
            temperature=decision.temperature,
            urgency=decision.urgency,
            action="operator_send_requested",
            suggested_body=decision.suggested_body,
            confidence=decision.confidence,
            policy_reason="Operator send requested",
            prompt_version=decision.prompt_version,
            provider_kind="operator",
            metadata={
                "parent_decision_id": decision.id,
                "operator_approval": True,
            },
        )
    )

    with pytest.raises(SmsAgentSendRequestConflict, match="SMS send already requested"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == [
        "draft_only",
        "operator_send_requested",
    ]


def test_sms_agent_approve_send_rejects_approved_follow_up_without_send() -> None:
    sent_requests: list[dict] = []

    def fake_sender(request: dict) -> dict:
        sent_requests.append(request)
        return {"sid": "SM123", "status": "queued"}

    service, repository, contacts = _service_with_repository(
        request_sender=fake_sender
    )
    lead = _persisted_contact(contacts)
    job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )
    response = service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))
    follow_up = next(entry for entry in repository.list_decisions() if entry.action == "operator_approved_send")

    with pytest.raises(ValueError, match="Only draft_only SMS agent decisions can be approved"):
        service.approve_send(follow_up.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert response.provider_message_id == "SM123"
    assert len(sent_requests) == 1
    assert [entry.action for entry in repository.list_decisions(business_id=job.business_id, environment=job.environment)] == [
        "draft_only",
        "operator_send_requested",
        "operator_approved_send",
    ]


def test_sms_agent_approve_send_atomic_claim_conflict_prevents_second_provider_call() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"}
    )
    lead = _persisted_contact(contacts)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )
    repository.record_operator_send_request(
        SmsAgentReplyDecisionCreate(
            business_id=decision.business_id,
            environment=decision.environment,
            job_id=decision.job_id,
            message_id=decision.message_id,
            conversation_id=decision.conversation_id,
            contact_id=decision.contact_id,
            intent=decision.intent,
            source_lane=decision.source_lane,
            temperature=decision.temperature,
            urgency=decision.urgency,
            action="operator_send_requested",
            suggested_body=decision.suggested_body,
            confidence=decision.confidence,
            policy_reason="Operator send requested",
            prompt_version=decision.prompt_version,
            provider_kind="operator",
            metadata={
                "parent_decision_id": decision.id,
                "operator_approval": True,
            },
        )
    )

    with pytest.raises(SmsAgentSendRequestConflict, match="SMS send already requested"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []


def test_sms_agent_approve_send_rejects_without_job_or_contact_consent() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {}
    )
    lead = contacts.upsert_lead(
        LeadUpsertRequest(
            business_id="limitless",
            environment="dev",
            first_name="Maya",
            phone="+15551234567",
            property_address="123 Main St, Houston, TX",
            sms_consent=False,
        )
    )
    _job, decision = _persisted_sms_decision(repository, job_metadata={}, contact_id=lead.id)

    with pytest.raises(ValueError, match="SMS consent is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_rejects_contact_from_wrong_tenant_without_send() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"}
    )
    lead = _persisted_contact(contacts, business_id="other", sms_consent=True)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    with pytest.raises(ValueError, match="resolved contact is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_rejects_contact_phone_mismatch_without_send() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"}
    )
    lead = _persisted_contact(contacts, phone="+15559876543", sms_consent=True)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    with pytest.raises(ValueError, match="resolved contact is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_rejects_missing_body_without_send() -> None:
    sent_requests: list[dict] = []
    service, repository, _contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {}
    )
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        suggested_body=None,
    )

    with pytest.raises(ValueError, match="SMS body is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    with pytest.raises(ValueError, match="SMS body is required"):
        service.approve_send(
            decision.id,
            SmsAgentApproveSendRequest(operator_approval=True, edited_body="   "),
        )

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_rejects_missing_resolved_contact_without_send() -> None:
    sent_requests: list[dict] = []
    service, repository, _contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {}
    )
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=None,
    )

    with pytest.raises(ValueError, match="resolved contact is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_rejects_non_contact_identifier_without_send() -> None:
    sent_requests: list[dict] = []
    service, repository, _contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"}
    )
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id="lead_1",
    )

    with pytest.raises(ValueError, match="resolved contact is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_rejects_missing_contact_record_without_send_marker() -> None:
    sent_requests: list[dict] = []
    service, repository, _contacts = _service_with_repository(
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"}
    )
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id="ctc_missing",
    )

    with pytest.raises(ValueError, match="resolved contact is required"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_preflight_config_failure_leaves_no_send_marker() -> None:
    sent_requests: list[dict] = []
    service, repository, contacts = _service_with_repository(
        settings=Settings(_env_file=None, provider_live_sends_enabled=True),
        request_sender=lambda request: sent_requests.append(request) or {"sid": "SM_SHOULD_NOT_SEND"},
    )
    lead = _persisted_contact(contacts)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    with pytest.raises(RuntimeError, match="TEXTGRID_ACCOUNT_SID"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    assert sent_requests == []
    assert [entry.action for entry in repository.list_decisions()] == ["draft_only"]


def test_sms_agent_approve_send_records_requested_and_failed_follow_ups_when_send_fails() -> None:
    def failing_sender(request: dict) -> dict:
        raise RuntimeError("provider unavailable")

    service, repository, contacts = _service_with_repository(request_sender=failing_sender)
    lead = _persisted_contact(contacts)
    _job, decision = _persisted_sms_decision(
        repository,
        job_metadata={"sms_consent": True},
        contact_id=lead.id,
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        service.approve_send(decision.id, SmsAgentApproveSendRequest(operator_approval=True))

    decisions = repository.list_decisions()
    assert [entry.action for entry in decisions] == [
        "draft_only",
        "operator_send_requested",
        "operator_send_failed",
    ]
    assert decisions[1].metadata["parent_decision_id"] == decision.id
    assert decisions[2].metadata["parent_decision_id"] == decision.id
    assert decisions[2].metadata["error_message"] == "provider unavailable"


def test_sms_agent_live_send_builds_textgrid_request_and_logs_message() -> None:
    sent_requests: list[dict] = []

    def fake_sender(request: dict) -> dict:
        sent_requests.append(request)
        return {"sid": "SM123", "status": "queued"}

    settings = Settings(
        _env_file=None,
        provider_live_sends_enabled=True,
        textgrid_account_sid="acct_123",
        textgrid_auth_token="token_123",
        textgrid_from_number="3467725914",
        textgrid_status_callback_url="https://runtime.example.com/sms-agent/webhooks/textgrid",
    )
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    service = SmsAgentService(
        settings=settings,
        conversations=ConversationsRepository(client=client, settings=settings),
        messages=MessagesRepository(client=client, settings=settings),
        request_sender=fake_sender,
    )

    response = service.send_message(
        SmsAgentSendRequest(
            business_id="limitless",
            environment="dev",
            contact_id="ctc_123",
            to="555-123-4567",
            body="Ares live-gated SMS",
            sms_consent_confirmed=True,
            metadata={"lane": "general"},
        )
    )

    assert response.dry_run is False
    assert response.status == "queued"
    assert response.provider_message_id == "SM123"
    assert response.message_id is not None
    assert response.conversation_id == "SM123"
    assert response.log_status == "logged"
    assert sent_requests[0]["payload"] == {
        "Body": "Ares live-gated SMS",
        "From": "+13467725914",
        "To": "+15551234567",
        "StatusCallback": "https://runtime.example.com/sms-agent/webhooks/textgrid",
    }


def test_sms_agent_live_send_requires_textgrid_config() -> None:
    service = SmsAgentService(settings=Settings(_env_file=None, provider_live_sends_enabled=True))

    try:
        service.send_message(
            SmsAgentSendRequest(
                business_id="limitless",
                environment="dev",
                contact_id="ctc_123",
                to="555-123-4567",
                body="Ares SMS",
                sms_consent_confirmed=True,
            )
        )
    except RuntimeError as exc:
        assert "TEXTGRID_ACCOUNT_SID" in str(exc)
        assert "TEXTGRID_AUTH_TOKEN" in str(exc)
        assert "TEXTGRID_FROM_NUMBER" in str(exc)
    else:
        raise AssertionError("Expected missing TextGrid config to raise")


def test_sms_agent_live_send_requires_contact_and_consent() -> None:
    service = SmsAgentService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            textgrid_account_sid="acct_123",
            textgrid_auth_token="token_123",
            textgrid_from_number="3467725914",
        )
    )

    try:
        service.send_message(
            SmsAgentSendRequest(
                business_id="limitless",
                environment="dev",
                to="555-123-4567",
                body="Ares SMS",
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "contact_id is required for live SMS sends"
    else:
        raise AssertionError("Expected missing contact_id to raise")

    try:
        service.send_message(
            SmsAgentSendRequest(
                business_id="limitless",
                environment="dev",
                contact_id="ctc_123",
                to="555-123-4567",
                body="Ares SMS",
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "sms_consent_confirmed is required for live SMS sends"
    else:
        raise AssertionError("Expected missing consent confirmation to raise")
