from __future__ import annotations

from copy import deepcopy

from app.db.agent_installs import AgentInstallsRepository
from app.db.agents import AgentsRepository
from app.db.audit import AuditRepository
from app.db.catalog import CatalogRepository
from app.models.agent_installs import AgentInstallCreateRequest, AgentInstallListResponse, AgentInstallResponse
from app.models.agents import AgentCreateRequest
from app.services._control_plane_runtime import (
    StoreBoundControlPlaneClient,
    resolve_repository_for_active_backend,
    restore_store_from_snapshot,
)
from app.services.agent_registry_service import AgentRegistryService, agent_registry_service
from app.services.audit_service import AuditService
from app.services.catalog_service import CatalogService


class AgentInstallService:
    def __init__(self, repository: AgentInstallsRepository | None = None) -> None:
        self.repository = repository or AgentInstallsRepository()

    def _installs_repository(self) -> AgentInstallsRepository:
        self.repository = resolve_repository_for_active_backend(
            self.repository,
            factory=lambda client: AgentInstallsRepository(client=client),
        )
        return self.repository

    def create_install(self, request: AgentInstallCreateRequest, *, org_id: str) -> AgentInstallResponse:
        installs_repository = self._installs_repository()
        with installs_repository.client.transaction() as store:
            snapshot = deepcopy(store)
            transaction_client = StoreBoundControlPlaneClient(
                store,
                backend=getattr(installs_repository.client, "backend", "memory"),
            )
            transaction_catalog_service = CatalogService(
                repository=CatalogRepository(client=transaction_client),
            )
            transaction_audit = AuditService(audit_repository=AuditRepository(client=transaction_client))
            transaction_agent_registry = AgentRegistryService(
                agents_repository=AgentsRepository(client=transaction_client),
                audit=transaction_audit,
            )
            transaction_installs = AgentInstallsRepository(client=transaction_client)

            try:
                entry = transaction_catalog_service.get_entry(request.catalog_entry_id, org_id=org_id)
                if entry is None:
                    raise LookupError("Catalog entry not found")

                source = transaction_agent_registry.get_agent(entry.agent_id, org_id=org_id)
                if source is None:
                    raise LookupError("Catalog source agent not found")
                source_revision = next((revision for revision in source.revisions if revision.id == entry.agent_revision_id), None)
                if source_revision is None:
                    raise LookupError("Catalog source revision not found")
                if source_revision.state.value == "archived":
                    raise ValueError("Archived catalog revisions cannot be installed")

                created = transaction_agent_registry.create_agent(
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

                install = transaction_installs.create(
                    org_id=org_id,
                    catalog_entry_id=entry.id,
                    source_agent_id=source.agent.id,
                    source_agent_revision_id=source_revision.id,
                    installed_agent_id=created.agent.id,
                    installed_agent_revision_id=created.revisions[0].id,
                    business_id=created.agent.business_id,
                    environment=created.agent.environment,
                )
                transaction_audit.append_event(
                    event_type="agent_installed_from_catalog",
                    summary=f"Installed agent {created.agent.id} from catalog entry {entry.id}",
                    org_id=org_id,
                    resource_type="agent_install",
                    resource_id=install.id,
                    agent_id=created.agent.id,
                    agent_revision_id=created.revisions[0].id,
                )
                return AgentInstallResponse(install=install, agent=created.agent, revisions=created.revisions)
            except Exception:
                restore_store_from_snapshot(store, snapshot)
                raise

    def get_install(self, install_id: str, *, org_id: str) -> AgentInstallResponse | None:
        install = self._installs_repository().get(install_id)
        if install is None or install.org_id != org_id:
            return None
        agent_response = agent_registry_service.get_agent(install.installed_agent_id, org_id=org_id)
        if agent_response is None:
            return None
        return AgentInstallResponse(install=install, agent=agent_response.agent, revisions=agent_response.revisions)

    def list_installs(self, *, org_id: str) -> AgentInstallListResponse:
        installs_repository = self._installs_repository()
        return AgentInstallListResponse(installs=installs_repository.list(org_id=org_id))


agent_install_service = AgentInstallService()
