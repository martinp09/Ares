from fastapi import APIRouter, HTTPException, Query

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
) -> MissionControlTurnsResponse:
    return mission_control_service.get_turns(business_id=business_id, environment=environment)


@router.get("/runs", response_model=MissionControlRunsResponse)
def get_runs(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
) -> MissionControlRunsResponse:
    return mission_control_service.get_runs(business_id=business_id, environment=environment)
