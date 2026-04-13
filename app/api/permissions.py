from fastapi import APIRouter, HTTPException

from app.models.permissions import PermissionListResponse, PermissionRecord, PermissionUpsertRequest
from app.services.permission_service import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.post("", response_model=PermissionRecord)
def upsert_permission(request: PermissionUpsertRequest) -> PermissionRecord:
    try:
        return permission_service.upsert_permission(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{agent_revision_id}", response_model=PermissionListResponse)
def list_permissions(agent_revision_id: str) -> PermissionListResponse:
    return permission_service.list_permissions(agent_revision_id)
