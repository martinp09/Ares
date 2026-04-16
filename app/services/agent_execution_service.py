from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.db.agents import AgentsRepository
from app.host_adapters.registry import HostAdapterRegistry, host_adapter_registry
from app.models.agents import AgentRevisionState
from app.models.host_adapters import HostAdapterDispatchRequest, HostAdapterDispatchResult
from app.services.skill_registry_service import SkillRegistryService, skill_registry_service


class AgentExecutionService:
    def __init__(
        self,
        agents_repository: AgentsRepository | None = None,
        skill_registry: SkillRegistryService | None = None,
        host_registry: HostAdapterRegistry | None = None,
    ) -> None:
        self.agents_repository = agents_repository or AgentsRepository()
        self.skill_registry = skill_registry or skill_registry_service
        self.host_registry = host_registry or host_adapter_registry

    def dispatch_revision(
        self,
        agent_revision_id: str,
        *,
        payload: dict[str, Any] | None = None,
        run_id: str | None = None,
        session_id: str | None = None,
    ) -> HostAdapterDispatchResult:
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        if revision.state == AgentRevisionState.ARCHIVED:
            raise ValueError("Archived revisions cannot be dispatched")
        if revision.state != AgentRevisionState.PUBLISHED:
            raise ValueError("Only published revisions can be dispatched")

        agent = self.agents_repository.get_agent(revision.agent_id)
        if agent is None:
            raise ValueError("Agent not found")

        skills = self.skill_registry.resolve_skills(revision.skill_ids)
        adapter = self.host_registry.get_adapter(revision.host_adapter_kind)
        request = HostAdapterDispatchRequest(
            agent_id=agent.id,
            agent_revision_id=revision.id,
            business_id=agent.business_id,
            environment=agent.environment,
            payload=deepcopy(payload if payload is not None else revision.config),
            host_adapter_config=deepcopy(revision.host_adapter_config),
            skills=skills,
            run_id=run_id,
            session_id=session_id,
        )
        return adapter.dispatch(request)


agent_execution_service = AgentExecutionService()
