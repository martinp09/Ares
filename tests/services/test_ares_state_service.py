from app.domains.ares import AresCounty
from app.domains.ares_workflows import AresWorkflowScope, AresWorkflowStepStatus
from app.services.ares_state_service import AresStateService


def test_state_service_remembers_progress_across_steps() -> None:
    service = AresStateService(max_retries_per_step=1)
    service.start_workflow(
        workflow_id="wf-1",
        scope=AresWorkflowScope(counties=[AresCounty.HARRIS]),
        step_ids=["pull_signals", "score"],
        initial_next_best_action="Pull county signals",
    )

    service.set_step_status(
        workflow_id="wf-1",
        step_id="pull_signals",
        status=AresWorkflowStepStatus.COMPLETED,
        detail="Pulled 5 records",
    )
    service.set_step_status(
        workflow_id="wf-1",
        step_id="score",
        status=AresWorkflowStepStatus.IN_PROGRESS,
    )
    service.update_next_best_action(workflow_id="wf-1", next_best_action="Generate outreach drafts")

    state = service.get_state("wf-1")
    assert [step.step_id for step in state.steps] == ["pull_signals", "score"]
    assert state.steps[0].status == AresWorkflowStepStatus.COMPLETED
    assert state.steps[1].status == AresWorkflowStepStatus.IN_PROGRESS
    assert state.next_best_action == "Generate outreach drafts"
    assert len(state.history) == 2


def test_state_service_handles_retry_then_fallback() -> None:
    service = AresStateService(max_retries_per_step=1)
    service.start_workflow(
        workflow_id="wf-2",
        scope=AresWorkflowScope(counties=[AresCounty.DALLAS]),
        step_ids=["pull_signals"],
        initial_next_best_action="Pull county signals",
    )

    first = service.record_retry_or_fallback(
        workflow_id="wf-2",
        step_id="pull_signals",
        reason="provider timeout",
        fallback_action="Escalate to operator",
    )
    second = service.record_retry_or_fallback(
        workflow_id="wf-2",
        step_id="pull_signals",
        reason="provider timeout again",
        fallback_action="Escalate to operator",
    )

    state = service.get_state("wf-2")
    assert first.retry_scheduled is True
    assert second.retry_scheduled is False
    assert state.steps[0].status == AresWorkflowStepStatus.FAILED
    assert state.next_best_action == "Escalate to operator"
    assert len(state.history) == 2


def test_starting_same_workflow_id_resets_retry_counters() -> None:
    service = AresStateService(max_retries_per_step=1)
    scope = AresWorkflowScope(counties=[AresCounty.HARRIS])

    service.start_workflow(
        workflow_id="wf-reset",
        scope=scope,
        step_ids=["pull_signals"],
        initial_next_best_action="Pull county signals",
    )
    exhausted = service.record_retry_or_fallback(
        workflow_id="wf-reset",
        step_id="pull_signals",
        reason="provider timeout",
        fallback_action="Escalate to operator",
    )
    assert exhausted.retry_count == 1

    service.start_workflow(
        workflow_id="wf-reset",
        scope=scope,
        step_ids=["pull_signals"],
        initial_next_best_action="Pull county signals",
    )
    restarted = service.record_retry_or_fallback(
        workflow_id="wf-reset",
        step_id="pull_signals",
        reason="provider timeout after restart",
        fallback_action="Escalate to operator",
    )

    assert restarted.retry_count == 1
    assert restarted.retry_scheduled is True
