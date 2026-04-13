from fastapi import APIRouter

from app.models.outcomes import OutcomeEvaluateRequest, OutcomeRecord
from app.services.outcome_service import outcome_service

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


@router.post("", response_model=OutcomeRecord)
def evaluate_outcome(request: OutcomeEvaluateRequest) -> OutcomeRecord:
    return outcome_service.evaluate_outcome(request)
