from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.organizations import OrganizationCreateRequest, OrganizationListResponse, OrganizationRecord
from app.services.organization_service import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRecord)
def create_organization(
    request: OrganizationCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrganizationRecord:
    try:
        return organization_service.create_organization(request, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=OrganizationListResponse)
def list_organizations(actor_context: ActorContext = Depends(actor_context_dependency)) -> OrganizationListResponse:
    return organization_service.list_organizations(actor_org_id=actor_context.org_id)


@router.get("/{org_id}", response_model=OrganizationRecord)
def get_organization(
    org_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> OrganizationRecord:
    organization = organization_service.get_organization(org_id, actor_org_id=actor_context.org_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization
