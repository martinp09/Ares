from __future__ import annotations

from app.db.outcomes import OutcomesRepository
from app.models.outcomes import OutcomeEvaluateRequest, OutcomeRecord


class OutcomeService:
    def __init__(self, outcomes_repository: OutcomesRepository | None = None) -> None:
        self.outcomes_repository = outcomes_repository or OutcomesRepository()

    def evaluate_outcome(self, request: OutcomeEvaluateRequest) -> OutcomeRecord:
        return self.outcomes_repository.create(
            outcome_name=request.outcome_name,
            artifact_type=request.artifact_type,
            artifact_payload=request.artifact_payload,
            rubric_criteria=request.rubric_criteria,
            evaluator_result=request.evaluator_result,
            passed=request.passed,
            failure_details=request.failure_details,
            run_id=request.run_id,
        )

    def get_outcome(self, outcome_id: str) -> OutcomeRecord | None:
        return self.outcomes_repository.get(outcome_id)


outcome_service = OutcomeService()
