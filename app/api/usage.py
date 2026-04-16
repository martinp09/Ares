from fastapi import APIRouter, Query

from app.models.usage import UsageCreateRequest, UsageEventKind, UsageResponse, UsageRecord
from app.services.usage_service import usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("", response_model=UsageRecord)
def record_usage(request: UsageCreateRequest) -> UsageRecord:
    return usage_service.record_usage(request)


@router.get("", response_model=UsageResponse)
def list_usage(
    org_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    agent_revision_id: str | None = Query(default=None),
    kind: UsageEventKind | None = Query(default=None),
    source_kind: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
) -> UsageResponse:
    return usage_service.list_usage(
        org_id=org_id,
        agent_id=agent_id,
        agent_revision_id=agent_revision_id,
        kind=kind,
        source_kind=source_kind,
        limit=limit,
    )
