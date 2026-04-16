import pytest

from app.db.agents import AgentsRepository
from app.models.commands import CommandPolicy
from app.models.providers import ProviderCapability
from app.services.hermes_tools_service import HermesToolInvokeRequest, HermesToolsService, ToolPermissionError
from app.services.run_service import reset_control_plane_state
from app.services.tool_hook_service import ToolHookService


def _create_revision(*, provider_capabilities: list[ProviderCapability] | None = None) -> str:
    agents_repository = AgentsRepository()
    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Hook Agent",
        description="Exercise tool hooks",
        config={"prompt": "Use tools carefully"},
        provider_capabilities=provider_capabilities,
    )
    return revision.id


def test_tool_hooks_capture_before_and_after_success() -> None:
    reset_control_plane_state()
    revision_id = _create_revision(provider_capabilities=[ProviderCapability.TOOL_CALLS])
    events: list[tuple[str, object]] = []

    hook_service = ToolHookService(
        before_hooks=[lambda context: events.append(("before", context.phase, context.tool_name, context.capability_allowed))],
        after_hooks=[lambda context: events.append(("after", context.phase, context.success, context.status_code))],
    )
    tools_service = HermesToolsService(tool_hook_service=hook_service)

    response, status_code = tools_service.invoke_tool(
        "run_market_research",
        HermesToolInvokeRequest(
            agent_revision_id=revision_id,
            business_id="limitless",
            environment="dev",
            idempotency_key="hook-001",
            payload={"topic": "austin landlords"},
        ),
    )

    assert status_code == 201
    assert response.command_type == "run_market_research"
    assert events[0][0] == "before"
    assert events[0][1] == "before_tool_call"
    assert events[1][0] == "after"
    assert events[1][1] == "after_tool_call"
    assert events[1][2] is True
    assert events[1][3] == 201


def test_tool_hooks_observe_failure_when_command_service_raises() -> None:
    reset_control_plane_state()
    revision_id = _create_revision(provider_capabilities=[ProviderCapability.TOOL_CALLS])
    events: list[tuple[str, object]] = []

    class ExplodingCommandService:
        def classify(self, tool_name: str) -> CommandPolicy:
            return CommandPolicy.SAFE_AUTONOMOUS

        def create_command(self, request, policy_override=None):
            raise RuntimeError("boom")

    hook_service = ToolHookService(
        before_hooks=[lambda context: events.append(("before", context.tool_name, context.phase))],
        after_hooks=[lambda context: events.append(("after", context.success, context.error_message, context.phase))],
    )
    tools_service = HermesToolsService(command_service=ExplodingCommandService(), tool_hook_service=hook_service)

    with pytest.raises(RuntimeError, match="boom"):
        tools_service.invoke_tool(
            "run_market_research",
            HermesToolInvokeRequest(
                agent_revision_id=revision_id,
                business_id="limitless",
                environment="dev",
                idempotency_key="hook-002",
                payload={"topic": "houston landlords"},
            ),
        )

    assert events[0] == ("before", "run_market_research", "before_tool_call")
    assert events[1][0] == "after"
    assert events[1][1] is False
    assert events[1][2] == "boom"
    assert events[1][3] == "after_tool_call"


def test_tool_invocation_rejects_revisions_without_tool_call_capability() -> None:
    reset_control_plane_state()
    revision_id = _create_revision(provider_capabilities=[ProviderCapability.STREAMING])
    tools_service = HermesToolsService()

    with pytest.raises(ToolPermissionError, match="not allowed"):
        tools_service.invoke_tool(
            "run_market_research",
            HermesToolInvokeRequest(
                agent_revision_id=revision_id,
                business_id="limitless",
                environment="dev",
                idempotency_key="hook-003",
                payload={"topic": "dallas absentee owners"},
            ),
        )

    listed = tools_service.list_tools(agent_revision_id=revision_id)
    run_tool = next(tool for tool in listed.tools if tool.name == "run_market_research")
    assert run_tool.capability_allowed is False
