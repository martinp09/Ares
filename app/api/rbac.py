from fastapi import APIRouter, HTTPException, Query

from app.models.rbac import (
    EffectivePermissionResponse,
    OrgPolicyListResponse,
    OrgPolicyRecord,
    OrgPolicyUpsertRequest,
    OrgRoleAssignmentCreateRequest,
    OrgRoleAssignmentListResponse,
    OrgRoleAssignmentRecord,
    OrgRoleCreateRequest,
    OrgRoleGrantCreateRequest,
    OrgRoleGrantListResponse,
    OrgRoleGrantRecord,
    OrgRoleListResponse,
    OrgRoleRecord,
)
from app.services.rbac_service import rbac_service

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.post("/roles", response_model=OrgRoleRecord)
def create_role(request: OrgRoleCreateRequest) -> OrgRoleRecord:
    return rbac_service.create_role(request)


@router.get("/roles", response_model=OrgRoleListResponse)
def list_roles(org_id: str | None = Query(default=None)) -> OrgRoleListResponse:
    return rbac_service.list_roles(org_id=org_id)


@router.post("/roles/{role_id}/grants", response_model=OrgRoleGrantRecord)
def create_role_grant(role_id: str, request: OrgRoleGrantCreateRequest) -> OrgRoleGrantRecord:
    payload = request.model_copy(update={"role_id": role_id})
    return rbac_service.grant_role_permission(payload)


@router.get("/roles/{role_id}/grants", response_model=OrgRoleGrantListResponse)
def list_role_grants(role_id: str) -> OrgRoleGrantListResponse:
    return rbac_service.list_grants(role_id)


@router.post("/assignments", response_model=OrgRoleAssignmentRecord)
def assign_role(request: OrgRoleAssignmentCreateRequest) -> OrgRoleAssignmentRecord:
    return rbac_service.assign_role(request)


@router.get("/assignments", response_model=OrgRoleAssignmentListResponse)
def list_assignments(agent_revision_id: str = Query(...)) -> OrgRoleAssignmentListResponse:
    return rbac_service.list_assignments(agent_revision_id)


@router.post("/policies", response_model=OrgPolicyRecord)
def upsert_org_policy(request: OrgPolicyUpsertRequest) -> OrgPolicyRecord:
    return rbac_service.upsert_org_policy(request)


@router.get("/policies", response_model=OrgPolicyListResponse)
def list_org_policies(org_id: str | None = Query(default=None)) -> OrgPolicyListResponse:
    return rbac_service.list_org_policies(org_id=org_id)


@router.get("/revisions/{revision_id}/effective", response_model=EffectivePermissionResponse)
def resolve_effective_permission(revision_id: str, tool_name: str = Query(...)) -> EffectivePermissionResponse:
    try:
        return rbac_service.resolve_effective_response(agent_revision_id=revision_id, tool_name=tool_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
