from __future__ import annotations

from dataclasses import dataclass

from app.domains.ares_workflows import (
    AresWorkflowHistoryEntry,
    AresWorkflowScope,
    AresWorkflowState,
    AresWorkflowStepState,
    AresWorkflowStepStatus,
)


@dataclass(frozen=True)
class AresStepFailure:
    workflow_id: str
    step_id: str
    reason: str
    retry_count: int
    fallback_action: str
    retry_scheduled: bool


class AresStateService:
    def __init__(self, *, max_retries_per_step: int = 1) -> None:
        self._max_retries_per_step = max_retries_per_step
        self._states: dict[str, AresWorkflowState] = {}
        self._step_retry_counts: dict[tuple[str, str], int] = {}
        self._event_seq = 0

    def start_workflow(
        self,
        *,
        workflow_id: str,
        scope: AresWorkflowScope,
        step_ids: list[str],
        initial_next_best_action: str,
    ) -> AresWorkflowState:
        stale_retry_keys = [key for key in self._step_retry_counts if key[0] == workflow_id]
        for retry_key in stale_retry_keys:
            self._step_retry_counts.pop(retry_key, None)
        state = AresWorkflowState(
            workflow_id=workflow_id,
            scope=scope,
            steps=[AresWorkflowStepState(step_id=step_id) for step_id in step_ids],
            next_best_action=initial_next_best_action,
        )
        self._states[workflow_id] = state
        return state.model_copy(deep=True)

    def get_state(self, workflow_id: str) -> AresWorkflowState:
        state = self._states[workflow_id]
        return state.model_copy(deep=True)

    def set_step_status(
        self,
        *,
        workflow_id: str,
        step_id: str,
        status: AresWorkflowStepStatus,
        detail: str | None = None,
    ) -> None:
        state = self._states[workflow_id]
        step = self._require_step(state=state, step_id=step_id)
        step.status = status
        step.detail = detail
        self._record(
            state=state,
            step_id=step_id,
            summary=f"Step {step_id} set to {status.value}",
        )

    def update_next_best_action(self, *, workflow_id: str, next_best_action: str) -> None:
        state = self._states[workflow_id]
        state.next_best_action = next_best_action

    def record_retry_or_fallback(
        self,
        *,
        workflow_id: str,
        step_id: str,
        reason: str,
        fallback_action: str,
    ) -> AresStepFailure:
        state = self._states[workflow_id]
        step = self._require_step(state=state, step_id=step_id)
        retry_key = (workflow_id, step_id)
        retry_count = self._step_retry_counts.get(retry_key, 0) + 1
        self._step_retry_counts[retry_key] = retry_count

        retry_scheduled = retry_count <= self._max_retries_per_step
        if retry_scheduled:
            step.status = AresWorkflowStepStatus.PENDING
            step.detail = f"Retry {retry_count}/{self._max_retries_per_step}: {reason}"
            state.next_best_action = f"Retry {step_id}: {reason}"
        else:
            step.status = AresWorkflowStepStatus.FAILED
            step.detail = reason
            state.next_best_action = fallback_action

        self._record(
            state=state,
            step_id=step_id,
            summary=f"Failure on {step_id}: {reason}",
        )
        return AresStepFailure(
            workflow_id=workflow_id,
            step_id=step_id,
            reason=reason,
            retry_count=retry_count,
            fallback_action=fallback_action,
            retry_scheduled=retry_scheduled,
        )

    def _record(self, *, state: AresWorkflowState, step_id: str, summary: str) -> None:
        self._event_seq += 1
        state.record_history(
            AresWorkflowHistoryEntry(
                event_id=f"evt-{self._event_seq}",
                step_id=step_id,
                summary=summary,
            )
        )

    def _require_step(self, *, state: AresWorkflowState, step_id: str) -> AresWorkflowStepState:
        for step in state.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(f"Unknown workflow step: {step_id}")
