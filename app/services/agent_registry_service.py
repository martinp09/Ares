from __future__ import annotations

from app.db.agents import AgentsRepository
from app.models.agents import AgentCreateRequest, AgentRecord, AgentResponse, AgentRevisionState


class AgentRegistryService:
    def __init__(self, agents_repository: AgentsRepository | None = None) -> None:
        self.agents_repository = agents_repository or AgentsRepository()

    def create_agent(self, request: AgentCreateRequest) -> AgentResponse:
        agent, revision = self.agents_repository.create_agent(
            business_id=request.business_id,
            environment=request.environment,
            name=request.name,
            description=request.description,
            config=request.config,
            host_adapter_kind=request.host_adapter_kind,
            skill_ids=request.skill_ids,
            host_adapter_config=request.host_adapter_config,
        )
        return AgentResponse(agent=agent, revisions=[revision])

    def get_agent(self, agent_id: str) -> AgentResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None:
            return None
        revisions = self.agents_repository.list_revisions(agent_id)
        return AgentResponse(agent=agent, revisions=revisions)

    def list_agents(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentRecord]:
        return self.agents_repository.list_agents(business_id=business_id, environment=environment)

    def get_agent_revision_state(self, agent: AgentRecord) -> AgentRevisionState | None:
        if agent.active_revision_id is not None:
            revision = self.agents_repository.get_revision(agent.active_revision_id)
            if revision is not None:
                return revision.state

        revisions = self.agents_repository.list_revisions(agent.id)
        if not revisions:
            return None
        latest = max(revisions, key=lambda revision: revision.revision_number)
        return latest.state

    def publish_revision(self, agent_id: str, revision_id: str) -> AgentResponse | None:
        result = self.agents_repository.publish_revision(agent_id, revision_id)
        if result is None:
            return None
        agent, _ = result
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))

    def archive_revision(self, agent_id: str, revision_id: str) -> AgentResponse | None:
        result = self.agents_repository.archive_revision(agent_id, revision_id)
        if result is None:
            return None
        agent, _ = result
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))

    def clone_revision(self, agent_id: str, revision_id: str) -> AgentResponse | None:
        result = self.agents_repository.clone_revision(agent_id, revision_id)
        if result is None:
            return None
        agent, _ = result
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))


agent_registry_service = AgentRegistryService()
