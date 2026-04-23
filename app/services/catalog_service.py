from __future__ import annotations

from app.db.catalog import CatalogRepository
from app.models.catalog import CatalogEntryCreateRequest, CatalogEntryListResponse, CatalogEntryRecord
from app.services._control_plane_runtime import resolve_repository_for_active_backend
from app.services.agent_registry_service import agent_registry_service
from app.services.audit_service import audit_service


class CatalogService:
    def __init__(self, repository: CatalogRepository | None = None) -> None:
        self.repository = repository or CatalogRepository()

    def _catalog_repository(self) -> CatalogRepository:
        self.repository = resolve_repository_for_active_backend(
            self.repository,
            factory=lambda client: CatalogRepository(client=client),
        )
        return self.repository

    def create_entry(self, request: CatalogEntryCreateRequest, *, org_id: str) -> CatalogEntryRecord:
        repository = self._catalog_repository()
        source = agent_registry_service.get_agent(request.agent_id, org_id=org_id)
        if source is None:
            raise LookupError("Agent revision not found")
        revision = next((item for item in source.revisions if item.id == request.agent_revision_id), None)
        if revision is None:
            raise LookupError("Agent revision not found")
        if revision.state.value == "archived":
            raise ValueError("Archived revisions cannot be cataloged")

        required_secret_names = [
            str(value)
            for value in revision.compatibility_metadata.get("requires_secrets", [])
            if isinstance(value, str) and value
        ]
        entry = repository.create(
            org_id=org_id,
            agent_id=source.agent.id,
            agent_revision_id=revision.id,
            slug=request.slug or source.agent.slug,
            name=request.name,
            summary=request.summary,
            description=request.description,
            visibility=source.agent.visibility,
            host_adapter_kind=revision.host_adapter_kind,
            provider_kind=revision.provider_kind,
            provider_capabilities=list(revision.provider_capabilities),
            required_skill_ids=list(revision.skill_ids),
            required_secret_names=required_secret_names,
            release_channel=revision.release_channel,
            metadata=request.metadata,
        )
        audit_service.append_event(
            event_type="catalog_entry_created",
            summary=f"Created catalog entry {entry.slug}",
            org_id=org_id,
            resource_type="catalog_entry",
            resource_id=entry.id,
            agent_id=entry.agent_id,
            agent_revision_id=entry.agent_revision_id,
        )
        return entry

    def get_entry(self, entry_id: str, *, org_id: str) -> CatalogEntryRecord | None:
        entry = self._catalog_repository().get(entry_id)
        if entry is None or entry.org_id != org_id:
            return None
        return entry

    def list_entries(self, *, org_id: str) -> CatalogEntryListResponse:
        return CatalogEntryListResponse(entries=self._catalog_repository().list(org_id=org_id))


catalog_service = CatalogService()
