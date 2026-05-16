import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_machine_supabase import LeadMachineTenant
from app.db.sms_agent import SmsAgentRepository
from app.models.sms_agent import SmsAgentJobCreate, SmsAgentReplyDecisionCreate


def _job_create(
    *,
    business_id: str = "limitless",
    environment: str = "dev",
    provider_webhook_id: str | None = "wh_1",
    message_id: str | None = "msg_1",
    conversation_id: str | None = "cnv_1",
    contact_id: str | None = "lead_1",
    from_number: str = "+15551234567",
    to_number: str = "+13467725914",
    payload_hash: str | None = None,
) -> SmsAgentJobCreate:
    return SmsAgentJobCreate(
        business_id=business_id,
        environment=environment,
        provider_webhook_id=provider_webhook_id,
        message_id=message_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        from_number=from_number,
        to_number=to_number,
        payload_hash=payload_hash,
    )


def _decision_create(
    *,
    business_id: str = "limitless",
    environment: str = "dev",
    job_id: str,
    message_id: str | None = "msg_1",
    conversation_id: str | None = "cnv_1",
    contact_id: str | None = "lead_1",
) -> SmsAgentReplyDecisionCreate:
    return SmsAgentReplyDecisionCreate(
        business_id=business_id,
        environment=environment,
        job_id=job_id,
        message_id=message_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        intent="interested",
        source_lane="seller_direct",
        temperature="warm",
        urgency="normal",
        action="draft_only",
        suggested_body="Thanks. I will have a human review and follow up.",
        confidence=0.76,
        policy_reason="Draft-only default",
        prompt_version="sms_reply_agent_v1",
    )


def test_sms_agent_repository_dedupes_jobs_by_webhook_receipt_and_message() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)

    first = repo.enqueue_job(_job_create())
    second = repo.enqueue_job(_job_create())

    assert second.id == first.id
    assert second.deduped is True


def test_sms_agent_repository_does_not_dedupe_jobs_without_durable_identity() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)

    first = repo.enqueue_job(
        _job_create(
            provider_webhook_id=None,
            message_id=None,
            payload_hash=None,
            conversation_id="cnv_1",
            contact_id="lead_1",
            from_number="+15551234567",
        )
    )
    second = repo.enqueue_job(
        _job_create(
            provider_webhook_id=None,
            message_id=None,
            payload_hash=None,
            conversation_id="cnv_2",
            contact_id="lead_2",
            from_number="+15557654321",
        )
    )

    assert second.id != first.id
    assert first.deduped is False
    assert second.deduped is False


def test_sms_agent_repository_claims_pending_jobs_and_records_decision() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())

    claimed = repo.claim_pending(limit=10, lock_seconds=120)
    assert [entry.id for entry in claimed] == [job.id]

    decision = repo.record_decision(_decision_create(job_id=job.id))
    repo.mark_completed(job.id, decision_id=decision.id)

    refreshed = repo.get_job(job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.decision_id == decision.id


def test_sms_agent_repository_mark_completed_preserves_existing_decision_id() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())
    decision = repo.record_decision(_decision_create(job_id=job.id))

    repo.mark_completed(job.id, decision_id=decision.id)
    completed = repo.mark_completed(job.id)

    assert completed is not None
    assert completed.decision_id == decision.id


def test_sms_agent_repository_mark_completed_requires_decision_audit() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())

    with pytest.raises(ValueError, match="decision_id is required to complete SMS agent job"):
        repo.mark_completed(job.id)


def test_sms_agent_repository_rejects_decision_for_wrong_tenant_job() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create(business_id="limitless", environment="dev"))

    with pytest.raises(ValueError):
        repo.record_decision(_decision_create(business_id="other", environment="dev", job_id=job.id))


def test_sms_agent_supabase_claim_rechecks_pending_and_unlocked_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []
    patch_calls: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return [{"id": 7, "attempt_count": 1}]

    def fake_patch_rows(
        table: str,
        *,
        params: dict[str, str],
        row: dict,
        select: str | None = None,
        settings: Settings | None = None,
    ) -> list[dict]:
        patch_calls.append({"table": table, "params": params, "row": row, "select": select, "settings": settings})
        return []

    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.sms_agent.patch_rows", fake_patch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)
    claimed = repo.claim_pending(limit=1, lock_seconds=120)

    assert claimed == []
    assert len(fetch_calls) == 1
    assert len(patch_calls) == 1
    assert patch_calls[0]["params"] == {
        "id": "eq.7",
        "status": "eq.pending",
        "or": fetch_calls[0]["params"]["or"],
    }


def test_sms_agent_supabase_enqueue_without_durable_identity_skips_existing_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []
    insert_calls: list[dict] = []

    def fake_resolve_tenant(business_id: str, environment: str, *, settings: Settings | None = None) -> LeadMachineTenant:
        return LeadMachineTenant(business_pk=1, environment=environment)

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return []

    def fake_insert_rows(
        table: str,
        rows: list[dict],
        *,
        select: str | None = None,
        prefer: str = "return=representation",
        settings: Settings | None = None,
    ) -> list[dict]:
        insert_calls.append({"table": table, "rows": rows, "select": select, "prefer": prefer, "settings": settings})
        return [
            {
                **rows[0],
                "id": 9,
                "status": "pending",
                "attempt_count": 0,
                "metadata": {},
                "created_at": "2026-05-16T09:00:00+00:00",
                "updated_at": "2026-05-16T09:00:00+00:00",
            }
        ]

    monkeypatch.setattr("app.db.sms_agent.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.sms_agent.insert_rows", fake_insert_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)
    job = repo.enqueue_job(_job_create(provider_webhook_id=None, message_id=None, payload_hash=None))

    assert job.id == "smsjob_9"
    assert fetch_calls == []
    assert insert_calls[0]["table"] == "sms_agent_jobs"


def test_sms_agent_supabase_mark_completed_preserves_existing_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []
    patch_calls: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return [
            {
                "id": 7,
                "business_id": 1,
                "environment": "dev",
                "provider_webhook_id": 1,
                "message_id": 1,
                "conversation_id": 1,
                "contact_id": 1,
                "from_number": "+15551234567",
                "to_number": "+13467725914",
                "status": "completed",
                "attempt_count": 1,
                "decision_id": 11,
                "metadata": {},
                "created_at": "2026-05-16T09:00:00+00:00",
                "updated_at": "2026-05-16T09:00:00+00:00",
            }
        ]

    def fake_patch_rows(
        table: str,
        *,
        params: dict[str, str],
        row: dict,
        select: str | None = None,
        settings: Settings | None = None,
    ) -> list[dict]:
        patch_calls.append({"table": table, "params": params, "row": row, "select": select, "settings": settings})
        return [{**fetch_calls[0]["params"], **fake_fetch_rows(table, params=params, settings=settings)[0], **row}]

    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.sms_agent.patch_rows", fake_patch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)
    completed = repo.mark_completed("smsjob_7")

    assert completed is not None
    assert completed.decision_id == "smsdec_11"
    assert fetch_calls[0]["table"] == "sms_agent_jobs"
    assert patch_calls[0]["row"]["decision_id"] == 11


def test_sms_agent_supabase_decision_hydrates_numeric_string_confidence() -> None:
    record = SmsAgentRepository._decision_from_supabase(
        {
            "id": 5,
            "business_id": 1,
            "environment": "dev",
            "job_id": 7,
            "intent": "interested",
            "source_lane": "seller_direct",
            "temperature": "warm",
            "urgency": "normal",
            "action": "draft_only",
            "confidence": "0.76",
            "policy_reason": "Draft-only default",
            "prompt_version": "sms_reply_agent_v1",
            "metadata": {},
            "created_at": "2026-05-16T09:00:00+00:00",
        }
    )

    assert record.confidence == 0.76


def test_sms_agent_supabase_record_decision_verifies_job_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []
    insert_calls: list[dict] = []

    def fake_resolve_tenant(business_id: str, environment: str, *, settings: Settings | None = None) -> LeadMachineTenant:
        return LeadMachineTenant(business_pk=1, environment=environment)

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return []

    def fake_insert_rows(
        table: str,
        rows: list[dict],
        *,
        select: str | None = None,
        prefer: str = "return=representation",
        settings: Settings | None = None,
    ) -> list[dict]:
        insert_calls.append({"table": table, "rows": rows, "select": select, "prefer": prefer, "settings": settings})
        return []

    monkeypatch.setattr("app.db.sms_agent.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.sms_agent.insert_rows", fake_insert_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)

    with pytest.raises(ValueError):
        repo.record_decision(_decision_create(job_id="smsjob_7"))

    assert fetch_calls == [
        {
            "table": "sms_agent_jobs",
            "params": {
                "select": "id",
                "id": "eq.7",
                "business_id": "eq.1",
                "environment": "eq.dev",
                "limit": "1",
            },
            "settings": repo.settings,
        }
    ]
    assert insert_calls == []


def test_sms_agent_reply_decision_rejects_string_confidence() -> None:
    with pytest.raises(ValidationError):
        SmsAgentReplyDecisionCreate(
            business_id="limitless",
            environment="dev",
            job_id="smsjob_1",
            intent="interested",
            source_lane="seller_direct",
            temperature="warm",
            urgency="normal",
            action="draft_only",
            confidence="0.76",
            policy_reason="Draft-only default",
            prompt_version="sms_reply_agent_v1",
        )
