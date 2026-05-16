from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.conversations import ConversationsRepository
from app.db.messages import MessagesRepository
from app.db.sms_agent import SmsAgentRepository
from app.models.sms_agent import SmsAgentJobCreate, SmsAgentJobRecord
from app.services.sms_agent_service import SmsAgentService


def _job_create(
    *,
    provider_webhook_id: str = "wh_1",
    message_id: str = "msg_1",
    contact_id: str = "lead_1",
    metadata: dict | None = None,
) -> SmsAgentJobCreate:
    return SmsAgentJobCreate(
        business_id="limitless",
        environment="dev",
        provider_webhook_id=provider_webhook_id,
        message_id=message_id,
        conversation_id="cnv_1",
        contact_id=contact_id,
        from_number="+15551234567",
        to_number="+13467725914",
        metadata=metadata or {},
    )


def test_sms_agent_process_pending_records_draft_decision_without_sending() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    repo.enqueue_job(
        _job_create(
            metadata={
                "body": "yes I am interested",
                "sms_consent": True,
                "source_lane": "outbound_probate",
            }
        )
    )
    sent_requests: list[dict] = []
    service = SmsAgentService(
        settings=Settings(_env_file=None, provider_live_sends_enabled=False),
        sms_agent_repository=repo,
        request_sender=sent_requests.append,
    )

    result = service.process_pending(limit=10)

    assert result == {
        "processed_count": 1,
        "sent_count": 0,
        "blocked_count": 0,
        "failed_count": 0,
    }
    assert sent_requests == []
    decisions = repo.list_decisions(business_id="limitless", environment="dev")
    assert len(decisions) == 1
    assert decisions[0].action == "draft_only"
    assert decisions[0].source_lane == "outbound_probate"


def test_sms_agent_process_pending_marks_send_failures_retryable_then_terminal() -> None:
    store = InMemoryControlPlaneStore()
    client = InMemoryControlPlaneClient(store)
    repo = SmsAgentRepository(client=client)
    retryable_job = repo.enqueue_job(
        _job_create(
            provider_webhook_id="wh_retryable",
            message_id="msg_retryable",
            metadata={
                "body": "yes I am interested",
                "sms_consent": True,
                "source_lane": "outbound_probate",
            },
        )
    )
    terminal_job = repo.enqueue_job(
        _job_create(
            provider_webhook_id="wh_terminal",
            message_id="msg_terminal",
            metadata={
                "body": "yes I am interested",
                "sms_consent": True,
                "source_lane": "outbound_probate",
            },
        )
    )
    with client.transaction() as transaction_store:
        existing = SmsAgentJobRecord.model_validate(transaction_store.sms_agent_jobs[terminal_job.id])
        transaction_store.sms_agent_jobs[terminal_job.id] = existing.model_copy(update={"attempt_count": 1})

    sent_requests: list[dict] = []

    def failing_sender(request: dict) -> dict:
        sent_requests.append(request)
        raise RuntimeError("provider unavailable")

    settings = Settings(
        _env_file=None,
        provider_live_sends_enabled=True,
        sms_agent_auto_replies_enabled=True,
        sms_agent_mode="auto_ack",
        sms_agent_max_attempts=2,
        textgrid_account_sid="acct_123",
        textgrid_auth_token="token_123",
        textgrid_from_number="3467725914",
    )
    service = SmsAgentService(
        settings=settings,
        conversations=ConversationsRepository(client=client, settings=settings),
        messages=MessagesRepository(client=client, settings=settings),
        sms_agent_repository=repo,
        request_sender=failing_sender,
    )

    result = service.process_pending(limit=10)

    assert result == {
        "processed_count": 2,
        "sent_count": 0,
        "blocked_count": 0,
        "failed_count": 2,
    }
    assert len(sent_requests) == 2
    retryable = repo.get_job(retryable_job.id)
    terminal = repo.get_job(terminal_job.id)
    assert retryable is not None
    assert retryable.status == "failed_retryable"
    assert retryable.last_error == "provider unavailable"
    assert retryable.decision_id is not None
    assert terminal is not None
    assert terminal.status == "failed_terminal"
    assert terminal.last_error == "provider unavailable"
    assert terminal.decision_id is not None
    decisions = repo.list_decisions(business_id="limitless", environment="dev")
    assert {decision.id for decision in decisions} == {retryable.decision_id, terminal.decision_id}
