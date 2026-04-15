from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.outcomes import OutcomeRecord, OutcomeStatus


class OutcomesRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        outcome_name: str,
        artifact_type: str,
        artifact_payload: dict,
        rubric_criteria: list[str],
        evaluator_result: str,
        passed: bool,
        failure_details: list[str],
        run_id: str | None,
    ) -> OutcomeRecord:
        outcome = OutcomeRecord(
            id=generate_id("out"),
            outcome_name=outcome_name,
            artifact_type=artifact_type,
            artifact_payload=deepcopy(artifact_payload),
            rubric_criteria=list(rubric_criteria),
            evaluator_result=evaluator_result,
            status=OutcomeStatus.SATISFIED if passed else OutcomeStatus.FAILED,
            satisfied=passed,
            failure_details=list(failure_details),
            run_id=run_id,
            created_at=utc_now(),
        )
        with self.client.transaction() as store:
            store.outcomes[outcome.id] = outcome
        return outcome

    def get(self, outcome_id: str) -> OutcomeRecord | None:
        with self.client.transaction() as store:
            return store.outcomes.get(outcome_id)
