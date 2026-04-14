from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from app.db.client import ControlPlaneClient, SupabaseControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.outcomes import OutcomeRecord, OutcomeStatus


def outcome_record_from_row(row: Mapping[str, Any]) -> OutcomeRecord:
    raw_artifact_payload = row.get("artifact_payload")
    artifact_payload = dict(raw_artifact_payload) if isinstance(raw_artifact_payload, Mapping) else {}
    raw_rubric_criteria = row.get("rubric_criteria")
    rubric_criteria = [str(item) for item in raw_rubric_criteria] if isinstance(raw_rubric_criteria, list) else []
    raw_failure_details = row.get("failure_details")
    failure_details = [str(item) for item in raw_failure_details] if isinstance(raw_failure_details, list) else []
    raw_satisfied = row.get("satisfied")
    satisfied = bool(raw_satisfied) if isinstance(raw_satisfied, bool) else str(row.get("status")) == OutcomeStatus.SATISFIED
    raw_status = row.get("status")
    status = OutcomeStatus(str(raw_status)) if raw_status is not None else (
        OutcomeStatus.SATISFIED if satisfied else OutcomeStatus.FAILED
    )

    return OutcomeRecord(
        id=str(row.get("runtime_id") or row["id"]),
        outcome_name=str(row["outcome_name"]),
        artifact_type=str(row["artifact_type"]),
        artifact_payload=artifact_payload,
        rubric_criteria=rubric_criteria,
        evaluator_result=str(row["evaluator_result"]),
        status=status,
        satisfied=satisfied,
        failure_details=failure_details,
        run_id=str(row["run_runtime_id"]) if row.get("run_runtime_id") is not None else None,
        created_at=row["created_at"],
    )


class OutcomesRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

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
        now = utc_now()
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
            created_at=now,
        )

        if self._is_supabase():
            rows = self._supabase_client().insert(
                "outcome_evaluations",
                rows=[
                    {
                        "runtime_id": outcome.id,
                        "outcome_name": outcome.outcome_name,
                        "artifact_type": outcome.artifact_type,
                        "artifact_payload": outcome.artifact_payload,
                        "rubric_criteria": outcome.rubric_criteria,
                        "evaluator_result": outcome.evaluator_result,
                        "status": outcome.status.value,
                        "satisfied": outcome.satisfied,
                        "failure_details": outcome.failure_details,
                        "run_runtime_id": outcome.run_id,
                        "created_at": now.isoformat(),
                    }
                ],
                columns=(
                    "id,runtime_id,outcome_name,artifact_type,artifact_payload,rubric_criteria,"
                    "evaluator_result,status,satisfied,failure_details,run_runtime_id,created_at"
                ),
            )
            if not rows:
                raise RuntimeError("Supabase outcome insert failed without returning a row")
            return outcome_record_from_row(rows[0])

        with self.client.transaction() as store:
            store.outcomes[outcome.id] = outcome
        return outcome

    def get(self, outcome_id: str) -> OutcomeRecord | None:
        if self._is_supabase():
            rows = self._supabase_client().select(
                "outcome_evaluations",
                columns=(
                    "id,runtime_id,outcome_name,artifact_type,artifact_payload,rubric_criteria,"
                    "evaluator_result,status,satisfied,failure_details,run_runtime_id,created_at"
                ),
                filters={"runtime_id": outcome_id},
                limit=1,
            )
            if not rows:
                return None
            return outcome_record_from_row(rows[0])

        with self.client.transaction() as store:
            return store.outcomes.get(outcome_id)
