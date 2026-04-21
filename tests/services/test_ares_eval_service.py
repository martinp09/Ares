from app.domains.ares import AresCounty
from app.domains.ares_workflows import AresWorkflowScope
from app.services.ares_eval_service import AresEvalService
from app.services.ares_state_service import AresStateService


def test_eval_service_surfaces_exceptions_in_report() -> None:
    state_service = AresStateService()
    state_service.start_workflow(
        workflow_id="wf-exc",
        scope=AresWorkflowScope(counties=[AresCounty.HARRIS]),
        step_ids=["pull_signals"],
        initial_next_best_action="Pull county signals",
    )
    state = state_service.get_state("wf-exc")

    service = AresEvalService()
    exc = service.capture_exception(
        workflow_id="wf-exc",
        step_id="pull_signals",
        message="county adapter unavailable",
    )
    report = service.evaluate(state=state, exceptions=[exc])

    assert report.workflow_id == "wf-exc"
    assert report.exception_count == 1
    assert report.surfaced_exceptions == ("wf-exc:pull_signals:county adapter unavailable",)
    assert report.suggested_next_action == "Escalate surfaced exceptions to operator review"


def test_eval_service_keeps_next_best_action_when_no_exceptions() -> None:
    state_service = AresStateService()
    state_service.start_workflow(
        workflow_id="wf-clean",
        scope=AresWorkflowScope(counties=[AresCounty.TRAVIS]),
        step_ids=["suggest_next_action"],
        initial_next_best_action="Route drafts to approval queue",
    )
    state = state_service.get_state("wf-clean")

    service = AresEvalService()
    report = service.evaluate(state=state, exceptions=[])

    assert report.exception_count == 0
    assert report.surfaced_exceptions == ()
    assert report.suggested_next_action == "Route drafts to approval queue"
