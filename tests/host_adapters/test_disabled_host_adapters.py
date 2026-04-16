from app.host_adapters.anthropic import AnthropicHostAdapter
from app.host_adapters.codex import CodexHostAdapter
from app.models.host_adapters import HostAdapterDispatchRequest, HostAdapterDispatchStatus


def build_request() -> HostAdapterDispatchRequest:
    return HostAdapterDispatchRequest(
        agent_id="agt_123",
        agent_revision_id="rev_123",
        business_id="limitless",
        environment="dev",
        payload={"prompt": "hello"},
    )


def test_codex_adapter_is_registered_but_disabled() -> None:
    adapter = CodexHostAdapter()

    result = adapter.dispatch(build_request())

    assert adapter.enabled is False
    assert result.status == HostAdapterDispatchStatus.DISABLED
    assert result.dispatch_id is None
    assert "disabled" in result.message


def test_anthropic_adapter_is_registered_but_disabled() -> None:
    adapter = AnthropicHostAdapter()

    result = adapter.dispatch(build_request())

    assert adapter.enabled is False
    assert result.status == HostAdapterDispatchStatus.DISABLED
    assert result.dispatch_id is None
    assert "disabled" in result.message
