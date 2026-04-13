from fastapi import APIRouter, HTTPException

from app.models.approvals import ApprovalDecisionRequest, ApprovalDecisionResponse
from app.services.approval_service import approval_service

router = APIRouter(tags=["approvals"])


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalDecisionResponse)
def approve(approval_id: str, request: ApprovalDecisionRequest) -> ApprovalDecisionResponse:
    response = approval_service.approve(approval_id, request)
    if response is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return response
