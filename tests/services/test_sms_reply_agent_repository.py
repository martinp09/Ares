from io import BytesIO
from urllib.error import HTTPError

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_machine_supabase import LeadMachineTenant
from app.db.sms_agent import SmsAgentRepository, SmsAgentSendRequestConflict
from app.models.sms_agent import SmsAgentEvalLabelRequest, SmsAgentJobCreate, SmsAgentReplyDecisionCreate


def _job_create(
    *,
    business_id: str = "limitless",
    environment: str = "dev",
    provider_webhook_id: str | None = "wh_1",
    message_id: str | None = "msg_1",
    conversation_id: str | None = "cnv_1",
    contact_id: str | None = "ctc_1",
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
    contact_id: str | None = "ctc_1",
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
            contact_id="ctc_1",
            from_number="+15551234567",
        )
    )
    second = repo.enqueue_job(
        _job_create(
            provider_webhook_id=None,
            message_id=None,
            payload_hash=None,
            conversation_id="cnv_2",
            contact_id="ctc_2",
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


def test_sms_agent_repository_mark_failed_preserves_existing_decision_id() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())
    decision = repo.record_decision(_decision_create(job_id=job.id))

    failed = repo.mark_failed(job.id, retryable=True, error_message="provider unavailable", decision_id=decision.id)
    failed_again = repo.mark_failed(job.id, retryable=False, error_message="provider still unavailable")

    assert failed is not None
    assert failed.decision_id == decision.id
    assert failed_again is not None
    assert failed_again.decision_id == decision.id


def test_sms_agent_repository_mark_completed_requires_decision_audit() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())

    with pytest.raises(ValueError, match="decision_id is required to complete SMS agent job"):
        repo.mark_completed(job.id)


def test_sms_agent_repository_lists_decisions_and_marks_failed() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())
    other_job = repo.enqueue_job(_job_create(business_id="other", provider_webhook_id="wh_2", message_id="msg_2"))

    first = repo.record_decision(_decision_create(job_id=job.id))
    repo.record_decision(_decision_create(business_id="other", job_id=other_job.id))
    failed = repo.mark_failed(job.id, retryable=True, error_message="provider unavailable")

    assert repo.list_decisions(business_id="limitless", environment="dev") == [first]
    assert failed is not None
    assert failed.status == "failed_retryable"
    assert failed.last_error == "provider unavailable"
    assert failed.locked_until is None


def test_sms_agent_repository_reclaims_retryable_failed_jobs() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())
    repo.mark_failed(job.id, retryable=True, error_message="provider unavailable")

    claimed = repo.claim_pending(limit=10, lock_seconds=120)

    assert [entry.id for entry in claimed] == [job.id]
    assert claimed[0].status == "processing"
    assert claimed[0].attempt_count == 1


def test_sms_agent_repository_records_eval_label_from_decision_tenant() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())
    decision = repo.record_decision(_decision_create(job_id=job.id))

    label = repo.record_eval_label(
        decision.id,
        SmsAgentEvalLabelRequest(
            label="correct",
            reviewer="operator",
            notes="approved draft",
            metadata={"source": "review_queue"},
        ),
    )

    assert label.id.startswith("smslbl_")
    assert label.decision_id == decision.id
    assert label.business_id == decision.business_id
    assert label.environment == decision.environment
    assert label.label == "correct"
    assert label.reviewer == "operator"
    assert repo.list_eval_labels(decision.id) == [label]
    assert repo.list_eval_labels("smsdec_missing") == []


def test_sms_agent_repository_rejects_eval_label_for_missing_decision() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)

    with pytest.raises(ValueError, match="SMS agent decision does not exist"):
        repo.record_eval_label("smsdec_missing", SmsAgentEvalLabelRequest(label="incorrect"))


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
        "status": "in.(pending,failed_retryable)",
        "or": fetch_calls[0]["params"]["or"],
    }
    assert fetch_calls[0]["params"]["status"] == "in.(pending,failed_retryable)"


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


def test_sms_agent_supabase_job_contact_id_serializes_and_hydrates_ctc_prefix() -> None:
    payload = SmsAgentRepository._job_payload_for_supabase(
        _job_create(contact_id="ctc_7"),
        business_pk=1,
        environment="dev",
    )
    record = SmsAgentRepository._job_from_supabase(
        {
            **payload,
            "id": 9,
            "status": "pending",
            "attempt_count": 0,
            "metadata": {},
            "created_at": "2026-05-16T09:00:00+00:00",
            "updated_at": "2026-05-16T09:00:00+00:00",
        }
    )

    assert payload["contact_id"] == 7
    assert record.contact_id == "ctc_7"


def test_sms_agent_supabase_decision_contact_id_serializes_and_hydrates_ctc_prefix() -> None:
    payload = SmsAgentRepository._decision_payload_for_supabase(
        _decision_create(job_id="smsjob_5", contact_id="ctc_7"),
        business_pk=1,
        environment="dev",
    )
    record = SmsAgentRepository._decision_from_supabase(
        {
            **payload,
            "id": 11,
            "metadata": {},
            "created_at": "2026-05-16T09:00:00+00:00",
        }
    )

    assert payload["contact_id"] == 7
    assert record.contact_id == "ctc_7"


def test_sms_agent_repository_operator_send_request_claim_conflicts_before_second_insert() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = SmsAgentRepository(client=client)
    job = repo.enqueue_job(_job_create())
    decision = repo.record_decision(_decision_create(job_id=job.id))
    create = _decision_create(job_id=job.id)
    marker_create = create.model_copy(
        update={
            "action": "operator_send_requested",
            "policy_reason": "Operator send requested",
            "provider_kind": "operator",
            "metadata": {"parent_decision_id": decision.id, "operator_approval": True},
        }
    )

    first = repo.record_operator_send_request(marker_create)
    with pytest.raises(SmsAgentSendRequestConflict, match="SMS send already requested"):
        repo.record_operator_send_request(marker_create)

    decisions = repo.list_decisions()
    assert [entry.action for entry in decisions] == ["draft_only", "operator_send_requested"]
    assert first.metadata["parent_decision_id"] == decision.id


def test_sms_agent_supabase_operator_send_request_maps_duplicate_insert_to_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_resolve_tenant(business_id: str, environment: str, *, settings: Settings | None = None) -> LeadMachineTenant:
        return LeadMachineTenant(business_pk=1, environment=environment)

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        return [{"id": 5}]

    def fake_insert_rows(
        table: str,
        rows: list[dict],
        *,
        select: str | None = None,
        prefer: str = "return=representation",
        settings: Settings | None = None,
    ) -> list[dict]:
        raise HTTPError(
            url="https://example.supabase.co/rest/v1/sms_agent_decisions",
            code=409,
            msg="Conflict",
            hdrs=None,
            fp=BytesIO(b'{"code":"23505","message":"duplicate key value violates unique constraint"}'),
        )

    monkeypatch.setattr("app.db.sms_agent.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.sms_agent.insert_rows", fake_insert_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)
    marker_create = _decision_create(job_id="smsjob_5").model_copy(
        update={
            "action": "operator_send_requested",
            "policy_reason": "Operator send requested",
            "provider_kind": "operator",
            "metadata": {"parent_decision_id": "smsdec_1", "operator_approval": True},
        }
    )

    with pytest.raises(SmsAgentSendRequestConflict, match="SMS send already requested"):
        repo.record_operator_send_request(marker_create)


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


def test_sms_agent_supabase_list_decisions_resolves_tenant_and_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []

    def fake_resolve_tenant(business_id: str, environment: str, *, settings: Settings | None = None) -> LeadMachineTenant:
        return LeadMachineTenant(business_pk=7, environment=environment)

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return []

    monkeypatch.setattr("app.db.sms_agent.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)

    assert repo.list_decisions(business_id="limitless", environment="dev") == []
    assert fetch_calls == [
        {
            "table": "sms_agent_decisions",
            "params": {
                "select": "*",
                "order": "created_at.asc,id.asc",
                "business_id": "eq.7",
                "environment": "eq.dev",
            },
            "settings": repo.settings,
        }
    ]


def test_sms_agent_supabase_list_decisions_requires_environment_for_slug_business_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return []

    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)

    with pytest.raises(ValueError, match="environment is required when filtering decisions by business_id"):
        repo.list_decisions(business_id="limitless")

    assert fetch_calls == []


def test_sms_agent_supabase_list_decisions_allows_numeric_business_id_without_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return []

    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)

    assert repo.list_decisions(business_id="7") == []
    assert fetch_calls == [
        {
            "table": "sms_agent_decisions",
            "params": {
                "select": "*",
                "order": "created_at.asc,id.asc",
                "business_id": "eq.7",
            },
            "settings": repo.settings,
        }
    ]


def test_sms_agent_supabase_mark_failed_patches_status_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_calls: list[dict] = []

    def fake_patch_rows(
        table: str,
        *,
        params: dict[str, str],
        row: dict,
        select: str | None = None,
        settings: Settings | None = None,
    ) -> list[dict]:
        patch_calls.append({"table": table, "params": params, "row": row, "select": select, "settings": settings})
        return [
            {
                "id": 7,
                "business_id": 1,
                "environment": "dev",
                "from_number": "+15551234567",
                "to_number": "+13467725914",
                "status": row["status"],
                "attempt_count": 2,
                "last_error": row["last_error"],
                "metadata": {},
                "created_at": "2026-05-16T09:00:00+00:00",
                "updated_at": "2026-05-16T09:00:00+00:00",
            }
        ]

    monkeypatch.setattr("app.db.sms_agent.patch_rows", fake_patch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)
    failed = repo.mark_failed("smsjob_7", retryable=False, error_message="provider unavailable")

    assert failed is not None
    assert failed.status == "failed_terminal"
    assert failed.last_error == "provider unavailable"
    assert patch_calls[0]["row"] == {
        "status": "failed_terminal",
        "last_error": "provider unavailable",
        "locked_until": None,
    }


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


def test_sms_agent_supabase_record_eval_label_verifies_decision_and_inserts_with_decision_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fetch_calls: list[dict] = []
    insert_calls: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return [{"id": 7, "business_id": 1, "environment": "dev"}]

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
                "id": 11,
                "created_at": "2026-05-16T09:00:00+00:00",
            }
        ]

    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.sms_agent.insert_rows", fake_insert_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)
    label = repo.record_eval_label(
        "smsdec_7",
        SmsAgentEvalLabelRequest(label="correct", reviewer="operator", metadata={"source": "review_queue"}),
    )

    assert label.id == "smslbl_11"
    assert fetch_calls == [
        {
            "table": "sms_agent_decisions",
            "params": {
                "select": "id,business_id,environment",
                "id": "eq.7",
                "limit": "1",
            },
            "settings": repo.settings,
        }
    ]
    assert insert_calls[0]["table"] == "sms_agent_eval_labels"
    assert insert_calls[0]["rows"] == [
        {
            "business_id": 1,
            "environment": "dev",
            "decision_id": 7,
            "label": "correct",
            "reviewer": "operator",
            "notes": None,
            "metadata": {"source": "review_queue"},
        }
    ]


def test_sms_agent_supabase_list_eval_labels_filters_decision_and_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    fetch_calls: list[dict] = []

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        fetch_calls.append({"table": table, "params": params, "settings": settings})
        return []

    monkeypatch.setattr("app.db.sms_agent.fetch_rows", fake_fetch_rows)

    repo = SmsAgentRepository(settings=Settings(lead_machine_backend="supabase"), force_memory=False)

    assert repo.list_eval_labels("smsdec_7") == []
    assert fetch_calls == [
        {
            "table": "sms_agent_eval_labels",
            "params": {
                "select": "*",
                "order": "created_at.asc,id.asc",
                "decision_id": "eq.7",
            },
            "settings": repo.settings,
        }
    ]


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
