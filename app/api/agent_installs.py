from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.agent_installs import AgentInstallCreateRequest, AgentInstallListResponse, AgentInstallResponse
from app.services.agent_install_service import agent_install_service

router = APIRouter(prefix="/agent-installs", tags=["agent-installs"])


@router.post("", response_model=AgentInstallResponse)
def create_agent_install(
    request: AgentInstallCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentInstallResponse:
    try:
        return agent_install_service.create_install(request, org_id=actor_context.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=AgentInstallListResponse)
def list_agent_installs(
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentInstallListResponse:
    return agent_install_service.list_installs(org_id=actor_context.org_id)


@router.get("/{install_id}", response_model=AgentInstallResponse)
def get_agent_install(
    install_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> AgentInstallResponse:
    install = agent_install_service.get_install(install_id, org_id=actor_context.org_id)
    if install is None:
        raise HTTPException(status_code=404, detail="Agent install not found")
    return install
