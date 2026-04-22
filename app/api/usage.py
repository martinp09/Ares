from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.usage import UsageCreateRequest, UsageEventKind, UsageResponse, UsageRecord
from app.services.usage_service import usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("", response_model=UsageRecord)
def record_usage(
    request: UsageCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> UsageRecord:
    try:
        return usage_service.record_usage(request, actor_context=actor_context)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=UsageResponse)
def list_usage(
    org_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    agent_revision_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    kind: UsageEventKind | None = Query(default=None),
    source_kind: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> UsageResponse:
    try:
        return usage_service.list_usage(
            org_id=org_id,
            actor_org_id=actor_context.org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            session_id=session_id,
            run_id=run_id,
            kind=kind,
            source_kind=source_kind,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
