from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.agents import AgentCreateRequest, AgentResponse
from app.services.agent_registry_service import agent_registry_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentResponse)
def create_agent(
    request: AgentCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentResponse:
    try:
        return agent_registry_service.create_agent(request.model_copy(update={"org_id": actor_context.org_id}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentResponse:
    response = agent_registry_service.get_agent(agent_id, org_id=actor_context.org_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return response


@router.post("/{agent_id}/revisions/{revision_id}/publish", response_model=AgentResponse)
def publish_revision(
    agent_id: str,
    revision_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentResponse:
    try:
        response = agent_registry_service.publish_revision(agent_id, revision_id, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if response is None:
        raise HTTPException(status_code=404, detail="Agent revision not found")
    return response


@router.post("/{agent_id}/revisions/{revision_id}/archive", response_model=AgentResponse)
def archive_revision(
    agent_id: str,
    revision_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentResponse:
    response = agent_registry_service.archive_revision(agent_id, revision_id, org_id=actor_context.org_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Agent revision not found")
    return response


@router.post("/{agent_id}/revisions/{revision_id}/clone", response_model=AgentResponse)
def clone_revision(
    agent_id: str,
    revision_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentResponse:
    response = agent_registry_service.clone_revision(agent_id, revision_id, org_id=actor_context.org_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Agent revision not found")
    return response
