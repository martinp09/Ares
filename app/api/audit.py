from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.audit import AuditAppendRequest, AuditListResponse, AuditRecord
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("", response_model=AuditRecord)
def append_audit_event(
    request: AuditAppendRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AuditRecord:
    try:
        return audit_service.append_event(request, actor_context=actor_context)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=AuditListResponse)
def list_audit_events(
    org_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    agent_revision_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AuditListResponse:
    try:
        return AuditListResponse(
            events=audit_service.list_events(
                org_id=org_id,
                actor_org_id=actor_context.org_id,
                agent_id=agent_id,
                agent_revision_id=agent_revision_id,
                session_id=session_id,
                run_id=run_id,
                resource_type=resource_type,
                resource_id=resource_id,
                event_type=event_type,
                limit=limit,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
