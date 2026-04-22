from __future__ import annotations

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.db.memberships import MembershipsRepository
from app.db.organizations import OrganizationsRepository
from app.models.organizations import MembershipCreateRequest, MembershipListResponse, MembershipRecord
from app.services.audit_service import audit_service


class AccessService:
    def __init__(
        self,
        memberships_repository: MembershipsRepository | None = None,
        organizations_repository: OrganizationsRepository | None = None,
    ) -> None:
        self.memberships_repository = memberships_repository or MembershipsRepository()
        self.organizations_repository = organizations_repository or OrganizationsRepository()

    @staticmethod
    def _resolve_request_org_id(request_org_id: str | None, *, actor_org_id: str | None = None) -> str | None:
        if actor_org_id is None:
            return request_org_id
        if request_org_id in (None, DEFAULT_INTERNAL_ORG_ID):
            return actor_org_id
        if request_org_id != actor_org_id:
            raise ValueError("Org id must match actor context")
        return actor_org_id

    @staticmethod
    def _resolve_list_org_id(request_org_id: str | None, *, actor_org_id: str | None = None) -> str | None:
        if actor_org_id is not None and request_org_id is not None and request_org_id != actor_org_id:
            raise ValueError("Org id must match actor context")
        return actor_org_id or request_org_id

    def create_membership(self, request: MembershipCreateRequest, *, org_id: str | None = None) -> MembershipRecord:
        effective_org_id = self._resolve_request_org_id(request.org_id, actor_org_id=org_id)
        if effective_org_id is None:
            raise ValueError("Org id is required")
        organization = self.organizations_repository.get(effective_org_id)
        if organization is None:
            raise ValueError("Organization not found")
        existing = self.memberships_repository.get_by_actor(org_id=effective_org_id, actor_id=request.actor_id)
        membership = self.memberships_repository.upsert(
            org_id=effective_org_id,
            actor_id=request.actor_id,
            actor_type=request.actor_type,
            member_id=request.member_id,
            name=request.name,
            role_name=request.role_name,
            metadata=request.metadata,
        )
        audit_service.append_event(
            event_type="membership_updated" if existing is not None else "membership_created",
            summary=f"{'Updated' if existing is not None else 'Created'} membership for {membership.actor_id}",
            org_id=membership.org_id,
            resource_type="membership",
            resource_id=membership.id,
            actor_id=membership.actor_id,
            actor_type=membership.actor_type,
            metadata={
                "member_id": membership.member_id,
                "role_name": membership.role_name,
                "name": membership.name,
            },
        )
        return membership

    def get_membership(self, membership_id: str, *, org_id: str | None = None) -> MembershipRecord | None:
        membership = self.memberships_repository.get(membership_id)
        if membership is None or (org_id is not None and membership.org_id != org_id):
            return None
        return membership

    def get_actor_membership(self, *, org_id: str, actor_id: str) -> MembershipRecord | None:
        return self.memberships_repository.get_by_actor(org_id=org_id, actor_id=actor_id)

    def list_memberships(
        self,
        *,
        org_id: str | None = None,
        actor_id: str | None = None,
        actor_org_id: str | None = None,
    ) -> MembershipListResponse:
        effective_org_id = self._resolve_list_org_id(org_id, actor_org_id=actor_org_id)
        return MembershipListResponse(memberships=self.memberships_repository.list(org_id=effective_org_id, actor_id=actor_id))


access_service = AccessService()
