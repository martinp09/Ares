from fastapi import APIRouter, HTTPException

from app.models.runs import RunDetailResponse
from app.services.run_service import run_service

router = APIRouter(tags=["runs"])


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str) -> RunDetailResponse:
    run = run_service.get_run_detail(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
