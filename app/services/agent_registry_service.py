from __future__ import annotations

from app.db.agents import AgentsRepository
from app.models.agents import AgentCreateRequest, AgentRecord, AgentResponse, AgentRevisionState
from app.models.providers import ProviderCapability, ProviderKind
from app.services.provider_registry_service import provider_registry_service
from app.services.skill_registry_service import skill_registry_service
from app.services.audit_service import audit_service


class AgentRegistryService:
    def __init__(self, agents_repository: AgentsRepository | None = None) -> None:
        self.agents_repository = agents_repository or AgentsRepository()

    def create_agent(self, request: AgentCreateRequest) -> AgentResponse:
        provider_entry = provider_registry_service.describe_provider(request.provider_kind)
        allowed_capabilities: list[str] = []
        if provider_entry.capabilities.streaming:
            allowed_capabilities.append("streaming")
        if provider_entry.capabilities.tool_calls:
            allowed_capabilities.append("tool_calls")
        if provider_entry.capabilities.json_schema:
            allowed_capabilities.append("json_schema")
        if provider_entry.capabilities.long_context:
            allowed_capabilities.append("long_context")

        requested_capabilities = [capability.value for capability in request.provider_capabilities]
        if requested_capabilities:
            invalid_capabilities = sorted(set(requested_capabilities) - set(allowed_capabilities))
            if invalid_capabilities:
                raise ValueError(
                    f"Provider '{request.provider_kind}' does not support capabilities: {', '.join(invalid_capabilities)}"
                )
            resolved_capabilities = requested_capabilities
        else:
            resolved_capabilities = allowed_capabilities

        if request.skill_ids:
            skill_registry_service.resolve_skills(request.skill_ids)

        agent, revision = self.agents_repository.create_agent(
            org_id=request.org_id,
            business_id=request.business_id,
            environment=request.environment,
            name=request.name,
            slug=request.slug,
            description=request.description,
            visibility=request.visibility,
            lifecycle_status=request.lifecycle_status,
            packaging_metadata=request.packaging_metadata,
            config=request.config,
            host_adapter_kind=request.host_adapter_kind,
            skill_ids=request.skill_ids,
            host_adapter_config=request.host_adapter_config,
            provider_kind=request.provider_kind,
            provider_config=request.provider_config,
            provider_capabilities=[ProviderCapability(capability) for capability in resolved_capabilities],
            input_schema=request.input_schema,
            output_schema=request.output_schema,
            release_notes=request.release_notes,
            compatibility_metadata=request.compatibility_metadata,
            release_channel=request.release_channel,
        )
        audit_service.append_event(
            event_type="agent_created",
            summary=f"Created agent {agent.name}",
            org_id=request.org_id,
            resource_type="agent",
            resource_id=agent.id,
            agent_id=agent.id,
            agent_revision_id=revision.id,
        )
        return AgentResponse(agent=agent, revisions=[revision])

    def get_agent(self, agent_id: str, *, org_id: str | None = None) -> AgentResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            return None
        revisions = self.agents_repository.list_revisions(agent_id)
        return AgentResponse(agent=agent, revisions=revisions)

    def list_agents(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentRecord]:
        return self.agents_repository.list_agents(org_id=org_id, business_id=business_id, environment=environment)

    def get_agent_revision_state(self, agent: AgentRecord) -> AgentRevisionState | None:
        if agent.active_revision_id is not None:
            revision = self.agents_repository.get_revision(agent.active_revision_id)
            if revision is not None:
                return revision.state

        revisions = self.agents_repository.list_revisions(agent.id)
        if not revisions:
            return None
        latest_visible_revision = max(
            (revision for revision in revisions if revision.state != AgentRevisionState.ARCHIVED),
            key=lambda revision: revision.revision_number,
            default=None,
        )
        latest = latest_visible_revision or max(revisions, key=lambda revision: revision.revision_number)
        return latest.state

    def promote_revision_to_candidate(
        self,
        agent_id: str,
        revision_id: str,
        *,
        org_id: str | None = None,
    ) -> AgentResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            return None
        result = self.agents_repository.promote_revision_to_candidate(agent_id, revision_id)
        if result is None:
            return None
        agent, revision = result
        audit_service.append_event(
            event_type="agent_candidate_promoted",
            summary=f"Promoted revision {revision.id} to candidate",
            org_id=agent.org_id,
            resource_type="agent_revision",
            resource_id=revision.id,
            agent_id=agent.id,
            agent_revision_id=revision.id,
        )
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))

    def publish_revision(self, agent_id: str, revision_id: str, *, org_id: str | None = None) -> AgentResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            return None
        result = self.agents_repository.publish_revision(agent_id, revision_id)
        if result is None:
            return None
        agent, revision = result
        audit_service.append_event(
            event_type="agent_published",
            summary=f"Published revision {revision.id}",
            org_id=agent.org_id,
            resource_type="agent_revision",
            resource_id=revision.id,
            agent_id=agent.id,
            agent_revision_id=revision.id,
        )
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))

    def archive_revision(self, agent_id: str, revision_id: str, *, org_id: str | None = None) -> AgentResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            return None
        result = self.agents_repository.archive_revision(agent_id, revision_id)
        if result is None:
            return None
        agent, revision = result
        audit_service.append_event(
            event_type="agent_archived",
            summary=f"Archived revision {revision.id}",
            org_id=agent.org_id,
            resource_type="agent_revision",
            resource_id=revision.id,
            agent_id=agent.id,
            agent_revision_id=revision.id,
        )
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))

    def get_revision_provider_kind(self, revision_id: str) -> ProviderKind | None:
        revision = self.agents_repository.get_revision(revision_id)
        if revision is None:
            return None
        return revision.provider_kind

    def get_revision_provider_spec(self, revision_id: str) -> dict[str, object] | None:
        revision = self.agents_repository.get_revision(revision_id)
        if revision is None:
            return None
        return {
            "provider_kind": revision.provider_kind,
            "provider_config": revision.provider_config,
            "provider_capabilities": revision.provider_capabilities,
        }

    def clone_revision(self, agent_id: str, revision_id: str, *, org_id: str | None = None) -> AgentResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            return None
        result = self.agents_repository.clone_revision(agent_id, revision_id)
        if result is None:
            return None
        agent, revision = result
        audit_service.append_event(
            event_type="agent_cloned",
            summary=f"Cloned revision {revision.id}",
            org_id=agent.org_id,
            resource_type="agent_revision",
            resource_id=revision.id,
            agent_id=agent.id,
            agent_revision_id=revision.id,
        )
        return AgentResponse(agent=agent, revisions=self.agents_repository.list_revisions(agent_id))


agent_registry_service = AgentRegistryService()
