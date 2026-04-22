from app.db.agents import AgentsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.db.skills import SkillsRepository
from app.host_adapters.registry import HostAdapterRegistry
from app.host_adapters.trigger_dev import TriggerDevHostAdapter
from app.models.agents import AgentRevisionState
from app.models.host_adapters import HostAdapterDispatchStatus, HostAdapterKind
from app.services.agent_execution_service import AgentExecutionService
from app.services.skill_registry_service import SkillRegistryService


def build_services() -> tuple[AgentsRepository, HostAdapterDispatchesRepository, AgentExecutionService]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    agents = AgentsRepository(client)
    skills = SkillRegistryService(SkillsRepository(client))
    dispatches = HostAdapterDispatchesRepository(client)
    registry = HostAdapterRegistry([TriggerDevHostAdapter(dispatches)])
    execution = AgentExecutionService(agents_repository=agents, skill_registry=skills, host_registry=registry)
    return agents, dispatches, execution


def test_agent_execution_dispatches_revision_through_resolved_host_adapter() -> None:
    agents, dispatches, execution = build_services()
    skill_registry = execution.skill_registry
    skill = skill_registry.register_skill(name="lead_triage")
    _, revision = agents.create_agent(
        business_id="limitless",
        environment="dev",
        name="Dispatch Agent",
        description=None,
        config={"prompt": "triage leads"},
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        skill_ids=[skill.id],
        host_adapter_config={"queue": "priority"},
    )
    agents.publish_revision(revision.agent_id, revision.id)

    result = execution.dispatch_revision(revision.id, payload={"lead_id": "lead_123"}, run_id="run_123")
    stored = dispatches.get(result.dispatch_id)

    assert result.status == HostAdapterDispatchStatus.ACCEPTED
    assert stored is not None
    assert stored.agent_revision_id == revision.id
    assert stored.external_reference == "run_123"
    assert stored.host_adapter_config == {"queue": "priority"}


def test_agent_execution_reuses_one_skill_across_multiple_agents() -> None:
    agents, dispatches, execution = build_services()
    skill_registry = execution.skill_registry
    skill = skill_registry.register_skill(name="lead_triage")

    _, first_revision = agents.create_agent(
        business_id="limitless",
        environment="dev",
        name="Dispatch Agent A",
        description=None,
        config={"prompt": "triage leads"},
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        skill_ids=[skill.id],
        host_adapter_config={},
    )
    _, second_revision = agents.create_agent(
        business_id="limitless",
        environment="dev",
        name="Dispatch Agent B",
        description=None,
        config={"prompt": "triage leads"},
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        skill_ids=[skill.id],
        host_adapter_config={},
    )
    agents.publish_revision(first_revision.agent_id, first_revision.id)
    agents.publish_revision(second_revision.agent_id, second_revision.id)

    first_result = execution.dispatch_revision(first_revision.id)
    second_result = execution.dispatch_revision(second_revision.id)

    first_dispatch = dispatches.get(first_result.dispatch_id)
    second_dispatch = dispatches.get(second_result.dispatch_id)

    assert first_result.status == HostAdapterDispatchStatus.ACCEPTED
    assert second_result.status == HostAdapterDispatchStatus.ACCEPTED
    assert first_dispatch is not None and first_dispatch.skill_ids == [skill.id]
    assert second_dispatch is not None and second_dispatch.skill_ids == [skill.id]


def test_agent_execution_rejects_archived_revisions() -> None:
    agents, _, execution = build_services()
    _, revision = agents.create_agent(
        business_id="limitless",
        environment="dev",
        name="Archived Agent",
        description=None,
        config={"prompt": "do not run"},
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        skill_ids=[],
        host_adapter_config={},
    )
    agents.archive_revision(revision.agent_id, revision.id)

    try:
        execution.dispatch_revision(revision.id)
    except ValueError as exc:
        assert str(exc) == "Archived revisions cannot be dispatched"
    else:
        raise AssertionError("Expected archived revision dispatch to fail")


def test_agent_execution_rejects_draft_revisions() -> None:
    agents, _, execution = build_services()
    _, revision = agents.create_agent(
        business_id="limitless",
        environment="dev",
        name="Draft Agent",
        description=None,
        config={"prompt": "wait for publish"},
        host_adapter_kind=HostAdapterKind.TRIGGER_DEV,
        skill_ids=[],
        host_adapter_config={},
    )

    try:
        execution.dispatch_revision(revision.id)
    except ValueError as exc:
        assert str(exc) == "Only published revisions can be dispatched"
    else:
        raise AssertionError("Expected draft revision dispatch to fail")


def test_agent_execution_rejects_disabled_adapters_without_breaking_registry_boot() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    agents = AgentsRepository(client)
    execution = AgentExecutionService(
        agents_repository=agents,
        skill_registry=SkillRegistryService(SkillsRepository(client)),
        host_registry=HostAdapterRegistry(),
    )
    _, revision = agents.create_agent(
        business_id="limitless",
        environment="dev",
        name="Codex Agent",
        description=None,
        config={"prompt": "future runtime"},
        host_adapter_kind=HostAdapterKind.CODEX,
        skill_ids=[],
        host_adapter_config={},
    )
    agents.publish_revision(revision.agent_id, revision.id)

    try:
        execution.dispatch_revision(revision.id)
    except ValueError as exc:
        assert str(exc) == "codex adapter is disabled in this environment"
    else:
        raise AssertionError("Expected disabled adapter dispatch to fail")
