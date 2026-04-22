from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.permissions import PermissionListResponse, PermissionRecord, PermissionUpsertRequest
from app.services.permission_service import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.post("", response_model=PermissionRecord)
def upsert_permission(
    request: PermissionUpsertRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> PermissionRecord:
    try:
        return permission_service.upsert_permission(request, org_id=actor_context.org_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 422
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/{agent_revision_id}", response_model=PermissionListResponse)
def list_permissions(
    agent_revision_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> PermissionListResponse:
    try:
        return permission_service.list_permissions(agent_revision_id, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
