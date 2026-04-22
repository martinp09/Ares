from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
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


def _status_code_for_rbac_error(message: str) -> int:
    return 404 if "not found" in message.lower() else 422


@router.post("/roles", response_model=OrgRoleRecord)
def create_role(
    request: OrgRoleCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgRoleRecord:
    try:
        return rbac_service.create_role(request, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.get("/roles", response_model=OrgRoleListResponse)
def list_roles(
    org_id: str | None = Query(default=None),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgRoleListResponse:
    try:
        return rbac_service.list_roles(org_id=org_id, actor_org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.post("/roles/{role_id}/grants", response_model=OrgRoleGrantRecord)
def create_role_grant(
    role_id: str,
    request: OrgRoleGrantCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgRoleGrantRecord:
    payload = request.model_copy(update={"role_id": role_id})
    try:
        return rbac_service.grant_role_permission(payload, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.get("/roles/{role_id}/grants", response_model=OrgRoleGrantListResponse)
def list_role_grants(
    role_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgRoleGrantListResponse:
    try:
        return rbac_service.list_grants(role_id, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.post("/assignments", response_model=OrgRoleAssignmentRecord)
def assign_role(
    request: OrgRoleAssignmentCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgRoleAssignmentRecord:
    try:
        return rbac_service.assign_role(request, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.get("/assignments", response_model=OrgRoleAssignmentListResponse)
def list_assignments(
    agent_revision_id: str = Query(...),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgRoleAssignmentListResponse:
    try:
        return rbac_service.list_assignments(agent_revision_id, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.post("/policies", response_model=OrgPolicyRecord)
def upsert_org_policy(
    request: OrgPolicyUpsertRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgPolicyRecord:
    try:
        return rbac_service.upsert_org_policy(request, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.get("/policies", response_model=OrgPolicyListResponse)
def list_org_policies(
    org_id: str | None = Query(default=None),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrgPolicyListResponse:
    try:
        return rbac_service.list_org_policies(org_id=org_id, actor_org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc


@router.get("/revisions/{revision_id}/effective", response_model=EffectivePermissionResponse)
def resolve_effective_permission(
    revision_id: str,
    tool_name: str = Query(...),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> EffectivePermissionResponse:
    try:
        return rbac_service.resolve_effective_response(
            agent_revision_id=revision_id,
            tool_name=tool_name,
            org_id=actor_context.org_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=_status_code_for_rbac_error(str(exc)), detail=str(exc)) from exc
