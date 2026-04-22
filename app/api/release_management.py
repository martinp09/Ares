from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.release_management import (
    ReleaseEventListResponse,
    ReleaseTransitionRequest,
    ReleaseTransitionResponse,
)
from app.services.release_management_service import release_management_service

router = APIRouter(prefix="/release-management", tags=["release-management"])


@router.get("/agents/{agent_id}/events", response_model=ReleaseEventListResponse)
def list_release_events(
    agent_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> ReleaseEventListResponse:
    response = release_management_service.list_events(agent_id, org_id=actor_context.org_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return response


@router.post("/agents/{agent_id}/revisions/{revision_id}/publish", response_model=ReleaseTransitionResponse)
def publish_revision(
    agent_id: str,
    revision_id: str,
    request: ReleaseTransitionRequest | None = None,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> ReleaseTransitionResponse:
    try:
        response = release_management_service.publish_revision(
            agent_id,
            revision_id,
            actor_context=actor_context,
            notes=request.notes if request is not None else None,
            evaluation_summary=request.evaluation_summary if request is not None else None,
            require_passing_evaluation=request.require_passing_evaluation if request is not None else False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="Agent revision not found")
    return response


@router.post("/agents/{agent_id}/revisions/{revision_id}/rollback", response_model=ReleaseTransitionResponse)
def rollback_revision(
    agent_id: str,
    revision_id: str,
    request: ReleaseTransitionRequest | None = None,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> ReleaseTransitionResponse:
    try:
        response = release_management_service.rollback_revision(
            agent_id,
            revision_id,
            actor_context=actor_context,
            notes=request.notes if request is not None else None,
            evaluation_summary=request.evaluation_summary if request is not None else None,
            rollback_reason=request.rollback_reason if request is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="Agent revision not found")
    return response
