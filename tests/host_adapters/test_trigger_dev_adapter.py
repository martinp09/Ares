from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.host_adapters.trigger_dev import TriggerDevHostAdapter
from app.models.commands import utc_now
from app.models.host_adapters import HostAdapterDispatchRequest, HostAdapterDispatchStatus
from app.models.skills import SkillRecord


def test_trigger_dev_adapter_records_dispatch_and_preserves_run_correlation_id() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    dispatches = HostAdapterDispatchesRepository(client)
    adapter = TriggerDevHostAdapter(dispatches)
    skill = SkillRecord(
        id="skl_demo",
        name="lead_triage",
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    result = adapter.dispatch(
        HostAdapterDispatchRequest(
            agent_id="agt_123",
            agent_revision_id="rev_123",
            business_id="limitless",
            environment="dev",
            payload={"lead_id": "lead_123"},
            host_adapter_config={"queue": "priority"},
            skills=[skill],
            run_id="run_123",
            session_id="ses_123",
        )
    )

    stored = dispatches.get(result.dispatch_id)

    assert result.status == HostAdapterDispatchStatus.ACCEPTED
    assert result.external_reference == "run_123"
    assert stored is not None
    assert stored.run_id == "run_123"
    assert stored.session_id == "ses_123"
    assert stored.skill_ids == ["skl_demo"]
    assert stored.host_adapter_config == {"queue": "priority"}
