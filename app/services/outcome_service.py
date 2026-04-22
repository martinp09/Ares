from __future__ import annotations

from app.db.outcomes import OutcomesRepository
from app.models.outcomes import (
    OutcomeEvaluateRequest,
    OutcomeEvaluationPayload,
    OutcomeRecord,
    ReleaseDecisionAction,
    ReleaseDecisionContext,
    ReleaseDecisionEvaluationSummary,
)


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
            release_decision=request.release_decision,
        )

    def record_release_decision_evaluation(
        self,
        *,
        agent_id: str,
        revision_id: str,
        action: ReleaseDecisionAction,
        evaluation: OutcomeEvaluationPayload,
        notes: str | None = None,
        require_passing_evaluation: bool = False,
        rollback_reason: str | None = None,
    ) -> OutcomeRecord:
        return self.evaluate_outcome(
            OutcomeEvaluateRequest(
                outcome_name=evaluation.outcome_name,
                artifact_type=evaluation.artifact_type,
                artifact_payload=evaluation.artifact_payload,
                rubric_criteria=evaluation.rubric_criteria,
                evaluator_result=evaluation.evaluator_result,
                passed=evaluation.passed,
                failure_details=evaluation.failure_details,
                release_decision=ReleaseDecisionContext(
                    agent_id=agent_id,
                    revision_id=revision_id,
                    action=action,
                    notes=notes,
                    require_passing_evaluation=require_passing_evaluation,
                    rollback_reason=rollback_reason,
                ),
            )
        )

    def summarize_release_evaluation(
        self,
        outcome: OutcomeRecord,
        *,
        require_passing_evaluation: bool,
        blocked_promotion: bool = False,
        rollback_reason: str | None = None,
    ) -> ReleaseDecisionEvaluationSummary:
        release_decision = outcome.release_decision
        return ReleaseDecisionEvaluationSummary(
            outcome_id=outcome.id,
            outcome_name=outcome.outcome_name,
            status=outcome.status,
            satisfied=outcome.satisfied,
            evaluator_result=outcome.evaluator_result,
            failure_details=list(outcome.failure_details),
            rubric_criteria=list(outcome.rubric_criteria),
            require_passing_evaluation=require_passing_evaluation,
            blocked_promotion=blocked_promotion,
            rollback_reason=rollback_reason
            or (release_decision.rollback_reason if release_decision is not None else None),
        )

    def get_outcome(self, outcome_id: str) -> OutcomeRecord | None:
        return self.outcomes_repository.get(outcome_id)


outcome_service = OutcomeService()
