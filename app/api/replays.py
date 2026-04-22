from fastapi import APIRouter, HTTPException, Response, status

from app.models.runs import ReplayRequest, ReplayResponse
from app.services.replay_service import replay_service

router = APIRouter(tags=["replays"])


@router.post("/replays/{run_id}", response_model=ReplayResponse)
def replay(run_id: str, request: ReplayRequest, response: Response) -> ReplayResponse:
    try:
        replay_result = replay_service.replay_run(run_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if replay_result is None:
        raise HTTPException(status_code=404, detail="Run not found")

    replay_response, status_code = replay_result
    response.status_code = status_code
    if status_code == status.HTTP_409_CONFLICT:
        response.status_code = status.HTTP_409_CONFLICT
    return replay_response
