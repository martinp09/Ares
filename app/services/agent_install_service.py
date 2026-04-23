from __future__ import annotations

from app.db.agent_installs import AgentInstallsRepository
from app.models.agent_installs import AgentInstallCreateRequest, AgentInstallListResponse, AgentInstallResponse
from app.models.agents import AgentCreateRequest
from app.services.agent_registry_service import agent_registry_service
from app.services.audit_service import audit_service
from app.services.catalog_service import catalog_service


class AgentInstallService:
    def __init__(self, repository: AgentInstallsRepository | None = None) -> None:
        self.repository = repository or AgentInstallsRepository()

    def create_install(self, request: AgentInstallCreateRequest, *, org_id: str) -> AgentInstallResponse:
        entry = catalog_service.get_entry(request.catalog_entry_id, org_id=org_id)
        if entry is None:
            raise LookupError("Catalog entry not found")

        source = agent_registry_service.get_agent(entry.agent_id, org_id=org_id)
        if source is None:
            raise LookupError("Catalog source agent not found")
        source_revision = next((revision for revision in source.revisions if revision.id == entry.agent_revision_id), None)
        if source_revision is None:
            raise LookupError("Catalog source revision not found")
        if source_revision.state.value == "archived":
            raise ValueError("Archived catalog revisions cannot be installed")

        created = agent_registry_service.create_agent(
            AgentCreateRequest(
                org_id=org_id,
                business_id=request.business_id,
                environment=request.environment,
                name=request.name or source.agent.name,
                slug=request.slug or source.agent.slug,
                description=request.description if request.description is not None else source.agent.description,
                visibility=source.agent.visibility,
                packaging_metadata={
                    **source.agent.packaging_metadata,
                    "catalog_entry_id": entry.id,
                    "source_agent_id": source.agent.id,
                    "source_agent_revision_id": source_revision.id,
                },
                config=source_revision.config,
                host_adapter_kind=source_revision.host_adapter_kind,
                host_adapter_config=source_revision.host_adapter_config,
                provider_kind=source_revision.provider_kind,
                provider_config=source_revision.provider_config,
                provider_capabilities=source_revision.provider_capabilities,
                skill_ids=source_revision.skill_ids,
                input_schema=source_revision.input_schema,
                output_schema=source_revision.output_schema,
                release_notes=source_revision.release_notes,
                compatibility_metadata=source_revision.compatibility_metadata,
                release_channel=source_revision.release_channel,
            )
        )

        install = self.repository.create(
            org_id=org_id,
            catalog_entry_id=entry.id,
            source_agent_id=source.agent.id,
            source_agent_revision_id=source_revision.id,
            installed_agent_id=created.agent.id,
            installed_agent_revision_id=created.revisions[0].id,
            business_id=created.agent.business_id,
            environment=created.agent.environment,
        )
        audit_service.append_event(
            event_type="agent_installed_from_catalog",
            summary=f"Installed agent {created.agent.id} from catalog entry {entry.id}",
            org_id=org_id,
            resource_type="agent_install",
            resource_id=install.id,
            agent_id=created.agent.id,
            agent_revision_id=created.revisions[0].id,
        )
        return AgentInstallResponse(install=install, agent=created.agent, revisions=created.revisions)

    def get_install(self, install_id: str, *, org_id: str) -> AgentInstallResponse | None:
        install = self.repository.get(install_id)
        if install is None or install.org_id != org_id:
            return None
        agent_response = agent_registry_service.get_agent(install.installed_agent_id, org_id=org_id)
        if agent_response is None:
            return None
        return AgentInstallResponse(install=install, agent=agent_response.agent, revisions=agent_response.revisions)

    def list_installs(self, *, org_id: str) -> AgentInstallListResponse:
        return AgentInstallListResponse(installs=self.repository.list(org_id=org_id))


agent_install_service = AgentInstallService()
