from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.host_adapters.trigger_dev import TriggerDevHostAdapter
from app.models.commands import utc_now
from app.models.host_adapters import (
    HostAdapterArtifactRecord,
    HostAdapterArtifactReportRequest,
    HostAdapterCancellationRequest,
    HostAdapterCorrelationRecord,
    HostAdapterDispatchRequest,
    HostAdapterDispatchStatus,
    HostAdapterStatusCorrelationRequest,
)
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
    assert result.correlation is not None
    assert result.correlation.dispatch_id == result.dispatch_id
    assert result.correlation.run_id == "run_123"
    assert result.correlation.session_id == "ses_123"
    assert result.correlation.external_reference == "run_123"
    assert stored is not None
    assert stored.run_id == "run_123"
    assert stored.session_id == "ses_123"
    assert stored.skill_ids == ["skl_demo"]
    assert stored.host_adapter_config == {"queue": "priority"}


def test_trigger_dev_adapter_exposes_status_correlation_and_artifact_contracts() -> None:
    adapter = TriggerDevHostAdapter()

    correlation = adapter.correlate_status(
        HostAdapterStatusCorrelationRequest(
            dispatch_id="had_123",
            run_id="run_123",
            session_id="ses_123",
        )
    )
    artifact_request = HostAdapterArtifactReportRequest(
        correlation=HostAdapterCorrelationRecord(
            dispatch_id="had_123",
            run_id="run_123",
            external_reference="run_123",
            adapter_details={"step": "before"},
        ),
        artifact=HostAdapterArtifactRecord(
            artifact_type="transcript",
            payload={"summary": "done"},
        ),
    )
    artifact = adapter.report_artifact(artifact_request)
    artifact_request.correlation.adapter_details["step"] = "after"
    artifact_request.artifact.payload["summary"] = "mutated"

    assert correlation.supported is True
    assert correlation.correlation is not None
    assert correlation.correlation.dispatch_id == "had_123"
    assert correlation.correlation.external_reference == "run_123"
    assert artifact.supported is True
    assert artifact.accepted is True
    assert artifact.correlation is not None
    assert artifact.correlation.run_id == "run_123"
    assert artifact.correlation.adapter_details == {"step": "before"}
    assert artifact.artifact is not None
    assert artifact.artifact.artifact_type == "transcript"
    assert artifact.artifact.payload == {"summary": "done"}


def test_trigger_dev_adapter_requires_dispatch_run_or_external_reference_for_status_correlation() -> None:
    adapter = TriggerDevHostAdapter()

    result = adapter.correlate_status(
        HostAdapterStatusCorrelationRequest(
            session_id="ses_only",
            adapter_reference="adapter_only",
            adapter_details={"source": "test"},
        )
    )

    assert result.supported is False
    assert result.correlation is None
    assert "requires dispatch_id, run_id, or external_reference" in result.message


def test_trigger_dev_adapter_cancellation_is_explicitly_unsupported() -> None:
    adapter = TriggerDevHostAdapter()

    result = adapter.cancel(
        HostAdapterCancellationRequest(
            correlation=HostAdapterCorrelationRecord(dispatch_id="had_123", run_id="run_123"),
            reason="operator requested stop",
        )
    )

    assert result.supported is False
    assert result.cancelled is False
    assert result.correlation is not None
    assert result.correlation.dispatch_id == "had_123"
    assert result.message == "trigger_dev adapter does not support cancellation"
