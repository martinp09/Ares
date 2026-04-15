from fastapi import APIRouter, HTTPException

from app.models.run_events import (
    ArtifactProducedCallbackRequest,
    RunCompletedCallbackRequest,
    RunFailedCallbackRequest,
    RunLifecycleResponse,
    RunStartedCallbackRequest,
)
from app.services.run_lifecycle_service import run_lifecycle_service

router = APIRouter(prefix="/trigger/callbacks", tags=["trigger-callbacks"])


@router.post("/runs/{run_id}/started", response_model=RunLifecycleResponse)
def mark_run_started(run_id: str, request: RunStartedCallbackRequest) -> RunLifecycleResponse:
    response = run_lifecycle_service.mark_run_started(run_id, request)
    if response is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return response


@router.post("/runs/{run_id}/completed", response_model=RunLifecycleResponse)
def mark_run_completed(run_id: str, request: RunCompletedCallbackRequest) -> RunLifecycleResponse:
    response = run_lifecycle_service.mark_run_completed(run_id, request)
    if response is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return response


@router.post("/runs/{run_id}/failed", response_model=RunLifecycleResponse)
def mark_run_failed(run_id: str, request: RunFailedCallbackRequest) -> RunLifecycleResponse:
    response = run_lifecycle_service.mark_run_failed(run_id, request)
    if response is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return response


@router.post("/runs/{run_id}/artifacts", response_model=RunLifecycleResponse)
def record_artifact(run_id: str, request: ArtifactProducedCallbackRequest) -> RunLifecycleResponse:
    response = run_lifecycle_service.record_artifact(run_id, request)
    if response is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return response
