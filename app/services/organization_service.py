from __future__ import annotations

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.db.organizations import OrganizationsRepository
from app.models.organizations import OrganizationCreateRequest, OrganizationListResponse, OrganizationRecord
from app.services._control_plane_runtime import resolve_repository_for_active_backend
from app.services.audit_service import audit_service


class OrganizationService:
    def __init__(self, organizations_repository: OrganizationsRepository | None = None) -> None:
        self.organizations_repository = organizations_repository or OrganizationsRepository()

    def _organizations_repository(self) -> OrganizationsRepository:
        self.organizations_repository = resolve_repository_for_active_backend(
            self.organizations_repository,
            factory=lambda client: OrganizationsRepository(client=client),
        )
        return self.organizations_repository

    @staticmethod
    def _resolve_request_org_id(request_org_id: str | None, *, actor_org_id: str | None = None) -> str | None:
        if actor_org_id is None:
            return request_org_id
        if request_org_id in (None, DEFAULT_INTERNAL_ORG_ID):
            return actor_org_id
        if request_org_id != actor_org_id:
            raise ValueError("Org id must match actor context")
        return actor_org_id

    def create_organization(self, request: OrganizationCreateRequest, *, org_id: str | None = None) -> OrganizationRecord:
        organizations_repository = self._organizations_repository()
        effective_org_id = self._resolve_request_org_id(request.id, actor_org_id=org_id)
        if effective_org_id is None:
            raise ValueError("Org id is required")
        existing = organizations_repository.get(effective_org_id)
        organization = organizations_repository.create(
            id=effective_org_id,
            name=request.name,
            slug=request.slug,
            metadata=request.metadata,
            is_internal=request.is_internal,
        )
        audit_service.append_event(
            event_type="organization_updated" if existing is not None else "organization_created",
            summary=f"{'Updated' if existing is not None else 'Created'} organization {organization.id}",
            org_id=organization.id,
            resource_type="organization",
            resource_id=organization.id,
            metadata={
                "name": organization.name,
                "slug": organization.slug,
                "is_internal": organization.is_internal,
            },
        )
        return organization

    def get_organization(self, org_id: str, *, actor_org_id: str | None = None) -> OrganizationRecord | None:
        if actor_org_id is not None and org_id != actor_org_id:
            return None
        return self._organizations_repository().get(org_id)

    def list_organizations(self, *, actor_org_id: str | None = None) -> OrganizationListResponse:
        organizations_repository = self._organizations_repository()
        if actor_org_id in (None, DEFAULT_INTERNAL_ORG_ID):
            return OrganizationListResponse(organizations=organizations_repository.list())
        organization = organizations_repository.get(actor_org_id)
        return OrganizationListResponse(organizations=[] if organization is None else [organization])


organization_service = OrganizationService()
