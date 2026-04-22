from app.host_adapters.anthropic import AnthropicHostAdapter
from app.host_adapters.codex import CodexHostAdapter
from app.models.host_adapters import (
    HostAdapterArtifactRecord,
    HostAdapterArtifactReportRequest,
    HostAdapterCancellationRequest,
    HostAdapterCorrelationRecord,
    HostAdapterDispatchRequest,
    HostAdapterDispatchStatus,
    HostAdapterStatusCorrelationRequest,
)


def build_request() -> HostAdapterDispatchRequest:
    return HostAdapterDispatchRequest(
        agent_id="agt_123",
        agent_revision_id="rev_123",
        business_id="limitless",
        environment="dev",
        payload={"prompt": "hello"},
        run_id="run_123",
        session_id="ses_123",
    )


def assert_disabled_contract(adapter) -> None:
    dispatch = adapter.dispatch(build_request())
    correlation = adapter.correlate_status(
        HostAdapterStatusCorrelationRequest(run_id="run_123", external_reference="run_123")
    )
    artifact = adapter.report_artifact(
        HostAdapterArtifactReportRequest(
            correlation=HostAdapterCorrelationRecord(run_id="run_123", external_reference="run_123"),
            artifact=HostAdapterArtifactRecord(artifact_type="trace", payload={"ok": False}),
        )
    )
    cancellation = adapter.cancel(
        HostAdapterCancellationRequest(
            correlation=HostAdapterCorrelationRecord(run_id="run_123", external_reference="run_123"),
            reason="disabled adapter",
        )
    )

    assert adapter.enabled is False
    assert adapter.describe().capabilities.dispatch is False
    assert dispatch.status == HostAdapterDispatchStatus.DISABLED
    assert dispatch.dispatch_id is None
    assert dispatch.disabled_reason == f"{adapter.kind.value} adapter is disabled in this environment"
    assert dispatch.correlation is not None
    assert dispatch.correlation.run_id == "run_123"
    assert dispatch.correlation.session_id == "ses_123"
    assert "disabled" in dispatch.message
    assert correlation.supported is False
    assert correlation.disabled_reason == f"{adapter.kind.value} adapter is disabled in this environment"
    assert artifact.supported is False
    assert artifact.accepted is False
    assert artifact.disabled_reason == f"{adapter.kind.value} adapter is disabled in this environment"
    assert cancellation.supported is False
    assert cancellation.cancelled is False
    assert cancellation.disabled_reason == f"{adapter.kind.value} adapter is disabled in this environment"


def test_codex_adapter_is_registered_but_disabled() -> None:
    assert_disabled_contract(CodexHostAdapter())


def test_anthropic_adapter_is_registered_but_disabled() -> None:
    assert_disabled_contract(AnthropicHostAdapter())
