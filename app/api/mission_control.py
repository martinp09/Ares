from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.mission_control import (
    MissionControlAgentsResponse,
    MissionControlApprovalsResponse,
    MissionControlAssetsResponse,
    MissionControlDashboardResponse,
    MissionControlEmailTestRequest,
    MissionControlInboxResponse,
    MissionControlOutboundSendResponse,
    MissionControlProvidersStatusResponse,
    MissionControlRunsResponse,
    MissionControlSmsTestRequest,
    MissionControlTasksResponse,
    MissionControlTurnsResponse,
)
from app.models.audit import AuditListResponse
from app.models.secrets import SecretBindingListResponse, SecretListResponse
from app.models.usage import UsageEventKind, UsageResponse
from app.services.mission_control_service import mission_control_service

router = APIRouter(prefix="/mission-control", tags=["mission-control"])


@router.get("/dashboard", response_model=MissionControlDashboardResponse)
def get_dashboard(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlDashboardResponse:
    return mission_control_service.get_dashboard(business_id=business_id, environment=environment)


@router.get("/inbox", response_model=MissionControlInboxResponse)
def get_inbox(
    selected_thread_id: str | None = Query(default=None),
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlInboxResponse:
    try:
        return mission_control_service.get_inbox(
            selected_thread_id=selected_thread_id,
            business_id=business_id,
            environment=environment,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Mission Control thread not found") from exc


@router.get("/tasks", response_model=MissionControlTasksResponse)
def get_tasks(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlTasksResponse:
    return mission_control_service.get_tasks(business_id=business_id, environment=environment)


@router.get("/approvals", response_model=MissionControlApprovalsResponse)
def get_approvals(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlApprovalsResponse:
    return mission_control_service.get_approvals(business_id=business_id, environment=environment)


@router.get("/agents", response_model=MissionControlAgentsResponse)
def get_agents(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlAgentsResponse:
    return mission_control_service.get_agents(business_id=business_id, environment=environment)


@router.get("/settings/assets", response_model=MissionControlAssetsResponse)
def get_assets(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlAssetsResponse:
    return mission_control_service.get_assets(business_id=business_id, environment=environment)


@router.get("/settings/secrets", response_model=SecretListResponse)
def get_secrets(org_id: str | None = Query(default=None)) -> SecretListResponse:
    return mission_control_service.get_secrets(org_id=org_id)


@router.get("/settings/secrets/revisions/{revision_id}", response_model=SecretBindingListResponse)
def get_secret_bindings(revision_id: str) -> SecretBindingListResponse:
    return mission_control_service.get_secret_bindings(revision_id=revision_id)


@router.get("/audit", response_model=AuditListResponse)
def get_audit(
    org_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    agent_revision_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
) -> AuditListResponse:
    return mission_control_service.get_audit(
        org_id=org_id,
        agent_id=agent_id,
        agent_revision_id=agent_revision_id,
        session_id=session_id,
        run_id=run_id,
        resource_type=resource_type,
        resource_id=resource_id,
        event_type=event_type,
        limit=limit,
    )


@router.get("/usage", response_model=UsageResponse)
def get_usage(
    org_id: str | None = Query(default=None),
    agent_id: str | None = Query(default=None),
    agent_revision_id: str | None = Query(default=None),
    kind: UsageEventKind | None = Query(default=None),
    source_kind: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1),
) -> UsageResponse:
    return mission_control_service.get_usage(
        org_id=org_id,
        agent_id=agent_id,
        agent_revision_id=agent_revision_id,
        kind=kind,
        source_kind=source_kind,
        limit=limit,
    )


@router.get("/providers/status", response_model=MissionControlProvidersStatusResponse)
def get_provider_status() -> MissionControlProvidersStatusResponse:
    return mission_control_service.get_provider_status()


@router.post("/outbound/sms/test", response_model=MissionControlOutboundSendResponse, status_code=201)
def send_test_sms(payload: MissionControlSmsTestRequest) -> MissionControlOutboundSendResponse:
    try:
        return mission_control_service.send_test_sms(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/outbound/email/test", response_model=MissionControlOutboundSendResponse, status_code=201)
def send_test_email(payload: MissionControlEmailTestRequest) -> MissionControlOutboundSendResponse:
    try:
        return mission_control_service.send_test_email(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/turns", response_model=MissionControlTurnsResponse)
def get_turns(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> MissionControlTurnsResponse:
    return mission_control_service.get_turns(
        org_id=actor_context.org_id,
        business_id=business_id,
        environment=environment,
    )


@router.get("/runs", response_model=MissionControlRunsResponse)
def get_runs(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlRunsResponse:
    return mission_control_service.get_runs(business_id=business_id, environment=environment)
