from pydantic import ValidationError

from app.domains.ares import AresCounty
from app.domains.ares_workflows import (
    AresWorkflowHistoryEntry,
    AresWorkflowScope,
    AresWorkflowState,
    AresWorkflowStepState,
    AresWorkflowStepStatus,
)


def test_workflow_models_represent_scope_state_and_next_best_action() -> None:
    workflow_state = AresWorkflowState(
        workflow_id="wf-harris-probate-001",
        scope=AresWorkflowScope(counties=[AresCounty.HARRIS]),
        steps=[
            AresWorkflowStepState(step_id="intake", status=AresWorkflowStepStatus.COMPLETED),
            AresWorkflowStepState(step_id="score", status=AresWorkflowStepStatus.IN_PROGRESS),
        ],
        next_best_action="Generate outreach drafts for top overlap leads",
    )

    assert workflow_state.scope.counties == [AresCounty.HARRIS]
    assert workflow_state.scope.market is None
    assert [step.step_id for step in workflow_state.steps] == ["intake", "score"]
    assert workflow_state.next_best_action.startswith("Generate outreach drafts")


def test_workflow_scope_accepts_market_slice_without_counties() -> None:
    scope = AresWorkflowScope(market="greater-houston")

    assert scope.market == "greater-houston"
    assert scope.counties == []


def test_workflow_scope_requires_counties_or_market() -> None:
    try:
        AresWorkflowScope()
    except ValidationError as exc:
        assert "counties or market" in str(exc)
    else:
        raise AssertionError("Expected workflow scope without counties/market to fail")


def test_workflow_history_records_happenings_without_losing_prior_entries() -> None:
    initial_entry = AresWorkflowHistoryEntry(
        event_id="evt-1",
        step_id="intake",
        summary="County intake completed",
    )
    workflow_state = AresWorkflowState(
        workflow_id="wf-dallas-probate-002",
        scope=AresWorkflowScope(counties=[AresCounty.DALLAS]),
        steps=[AresWorkflowStepState(step_id="intake", status=AresWorkflowStepStatus.COMPLETED)],
        next_best_action="Score leads",
        history=[initial_entry],
    )

    next_entry = AresWorkflowHistoryEntry(
        event_id="evt-2",
        step_id="score",
        summary="Scoring started",
    )
    workflow_state.record_history(next_entry)

    assert [entry.event_id for entry in workflow_state.history] == ["evt-1", "evt-2"]
    assert workflow_state.history[0].summary == "County intake completed"
    assert workflow_state.history[1].step_id == "score"
