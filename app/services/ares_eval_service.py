from __future__ import annotations

from dataclasses import dataclass

from app.domains.ares_workflows import AresWorkflowState, AresWorkflowStepStatus


@dataclass(frozen=True)
class AresWorkflowException:
    workflow_id: str
    step_id: str
    message: str


@dataclass(frozen=True)
class AresWorkflowEvalReport:
    workflow_id: str
    exception_count: int
    surfaced_exceptions: tuple[str, ...]
    suggested_next_action: str


class AresEvalService:
    def capture_exception(self, *, workflow_id: str, step_id: str, message: str) -> AresWorkflowException:
        return AresWorkflowException(workflow_id=workflow_id, step_id=step_id, message=message)

    def evaluate(
        self,
        *,
        state: AresWorkflowState,
        exceptions: list[AresWorkflowException],
    ) -> AresWorkflowEvalReport:
        surfaced = tuple(
            f"{exc.workflow_id}:{exc.step_id}:{exc.message}"
            for exc in exceptions
            if exc.workflow_id == state.workflow_id
        )
        failed_steps = [step.step_id for step in state.steps if step.status == AresWorkflowStepStatus.FAILED]
        if surfaced or failed_steps:
            action = "Escalate surfaced exceptions to operator review"
        else:
            action = state.next_best_action
        return AresWorkflowEvalReport(
            workflow_id=state.workflow_id,
            exception_count=len(surfaced),
            surfaced_exceptions=surfaced,
            suggested_next_action=action,
        )
