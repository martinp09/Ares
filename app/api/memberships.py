from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.organizations import MembershipCreateRequest, MembershipListResponse, MembershipRecord
from app.services.access_service import access_service

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.post("", response_model=MembershipRecord)
def create_membership(
    request: MembershipCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> MembershipRecord:
    try:
        return access_service.create_membership(request, org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=MembershipListResponse)
def list_memberships(
    org_id: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> MembershipListResponse:
    try:
        return access_service.list_memberships(org_id=org_id, actor_id=actor_id, actor_org_id=actor_context.org_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{membership_id}", response_model=MembershipRecord)
def get_membership(
    membership_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> MembershipRecord:
    membership = access_service.get_membership(membership_id, org_id=actor_context.org_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return membership
