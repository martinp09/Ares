from app.models.automation_runs import AutomationRunRecord, AutomationRunStatus


def test_automation_run_uses_replay_key_before_idempotency_key() -> None:
    record = AutomationRunRecord(
        business_id="limitless",
        environment="dev",
        workflow_name="lead-routing",
        status=AutomationRunStatus.IN_PROGRESS,
        idempotency_key="route-001",
        replay_key="tenant:lead-123:routing",
    )

    assert record.replay_safe_key() == "tenant:lead-123:routing"
    assert record.status == AutomationRunStatus.IN_PROGRESS


def test_automation_run_defaults_to_idempotency_key_when_replay_key_missing() -> None:
    record = AutomationRunRecord(
        business_id="limitless",
        environment="dev",
        workflow_name="lead-routing",
        idempotency_key="route-002",
    )

    assert record.replay_safe_key() == "route-002"
    assert record.deduped is False
