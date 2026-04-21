from app.domains.ares import AresCounty
from app.domains.ares_workflows import AresWorkflowStepStatus
from app.services.ares_playbook_service import AresPlaybookRunRequest, AresPlaybookService
from app.services.ares_state_service import AresStateService


def _county_fetcher(county: AresCounty) -> dict[str, tuple[dict[str, object], ...]]:
    if county == AresCounty.HARRIS:
        return {
            "probate": (
                {"property_address": " 123 Main St ", "owner_name": "Estate of Jane Doe"},
            ),
            "tax": (
                {"property_address": "123 Main St", "owner_name": "Jane Doe"},
            ),
        }
    if county == AresCounty.DALLAS:
        return {
            "probate": (
                {"property_address": "77 Elm St", "owner_name": "John Smith"},
            ),
            "tax": (),
        }
    return {"probate": (), "tax": ()}


def test_playbook_service_owns_workflow_from_intake_to_next_best_action() -> None:
    service = AresPlaybookService(county_fetcher=_county_fetcher)

    result = service.run(
        AresPlaybookRunRequest(
            workflow_id="wf-playbook-1",
            counties=(AresCounty.HARRIS, AresCounty.DALLAS),
            response_events=("positive_reply",),
        )
    )

    assert result.workflow_id == "wf-playbook-1"
    assert len(result.ranked_leads) >= 1
    assert len(result.briefs) == len(result.ranked_leads)
    assert len(result.drafts) == len(result.ranked_leads)
    assert len(result.follow_up_tasks) == len(result.drafts)
    assert result.next_best_action == "Prioritize live follow-up for positive responders"
    assert result.eval_report.exception_count == 0


def test_playbook_service_surfaces_fetch_exceptions_in_eval_report() -> None:
    def failing_fetcher(county: AresCounty) -> dict[str, tuple[dict[str, object], ...]]:
        if county == AresCounty.HARRIS:
            raise RuntimeError("harris source offline")
        return {"probate": (), "tax": ()}

    service = AresPlaybookService(county_fetcher=failing_fetcher)

    result = service.run(
        AresPlaybookRunRequest(
            workflow_id="wf-playbook-2",
            counties=(AresCounty.HARRIS,),
        )
    )

    assert result.eval_report.exception_count == 1
    assert "harris source offline" in result.eval_report.surfaced_exceptions[0]
    assert result.eval_report.suggested_next_action == "Escalate surfaced exceptions to operator review"


def test_playbook_service_does_not_overwrite_failed_pull_signals_step_to_completed() -> None:
    def failing_fetcher(county: AresCounty) -> dict[str, tuple[dict[str, object], ...]]:
        raise RuntimeError(f"{county.value} source offline")

    state_service = AresStateService(max_retries_per_step=0)
    service = AresPlaybookService(county_fetcher=failing_fetcher, state_service=state_service)

    result = service.run(
        AresPlaybookRunRequest(
            workflow_id="wf-playbook-3",
            counties=(AresCounty.HARRIS,),
        )
    )
    state = state_service.get_state("wf-playbook-3")
    pull_signals = next(step for step in state.steps if step.step_id == "pull_signals")

    assert result.eval_report.exception_count == 1
    assert pull_signals.status is AresWorkflowStepStatus.FAILED
    assert "source offline" in (pull_signals.detail or "")
